"""
The main application window and GUI controls

``MainWindow`` creates and handles the ``File | Open Device`` menu and
wraps the ``MainPanel`` widget responsible for most of the interface.

All the buttons and controls and their callback functions are built in
``MainPanel`` and arranged on a grid.  A ``Pyqtgraph Window`` is created
and placed to left of the controls.
"""

import sys
from PySide import QtGui, QtCore
import numpy as np
import math

from contextlib import contextmanager
from pkg_resources import parse_version

from pyrf.gui import colors
from pyrf.gui import labels
from pyrf.gui import gui_config

from pyrf.sweep_device import SweepDevice
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.config import TriggerSettings, TRIGGER_TYPE_LEVEL
from pyrf.capture_device import CaptureDevice
from pyrf.units import M
from pyrf.numpy_util import compute_fft
from pyrf.devices.thinkrf import WSA
from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)

from util import find_max_index, find_nearest_index
from util import hotkey_util, update_marker_traces
import control_util as cu
from plot_widget import Plot
from device_widget import DeviceControlsWidget
from discovery_widget import DiscoveryWidget

RBW_VALUES = [976.562, 488.281, 244.141, 122.070, 61.035, 30.518, 15.259, 7.62939, 3.815]

HDR_RBW_VALUES = [1271.56, 635.78, 317.890, 158.94, 79.475, 39.736, 19.868, 9.934]

PLOT_YMIN = -160
PLOT_YMAX = 20

ZIF_BITS = 2**13
CONST_POINTS = 512
try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass


class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, output_file=None):
        super(MainWindow, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        WINDOW_WIDTH = screen.width() * 0.7
        WINDOW_HEIGHT = screen.height() * 0.6
        self.resize(WINDOW_WIDTH,WINDOW_HEIGHT)
        self.initUI(output_file)

    def initUI(self, output_file):
        name = None
        if len(sys.argv) > 1:
            name = sys.argv[1]
        self.mainPanel = MainPanel(self,output_file)
        openAction = QtGui.QAction('&Open Device', self)
        openAction.triggered.connect( self.open_device_dialog)
        exitAction = QtGui.QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)
        self.setWindowTitle('Spectrum Analyzer')
        self.setCentralWidget(self.mainPanel)
        if name:
            self.mainPanel.open_device(name, True)
        else:
            self.open_device_dialog()

    def open_device_dialog(self):
        self.discovery_widget = DiscoveryWidget(
            open_device_callback=self.mainPanel.open_device,
            name="Open Device")
        self.discovery_widget.show()

    def closeEvent(self, event):
        if self.mainPanel.dut:
            self.mainPanel.dut.abort()
            self.mainPanel.dut.flush()
            self.mainPanel.dut.reset()
        event.accept()
        self.mainPanel._reactor.stop()

class MainPanel(QtGui.QWidget):
    """
    The spectrum view and controls
    """
    def __init__(self, main_window,output_file):
        self._main_window = main_window
        self.ref_level = 0
        self.dut = None
        self.control_widgets = []
        self._output_file = output_file
        super(MainPanel, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        self.setMinimumWidth(screen.width() * 0.7)
        self.setMinimumHeight(screen.height() * 0.6)
        self.plot_state = None
        # plot window
        self._plot = Plot(self)
        self._marker_trace = None
        self._vrt_context = {}
        self.initUI()
        self.disable_controls()
        self.ref_level = 0
        self._reactor = self._get_reactor()

    def _get_reactor(self):
        # late import because installReactor is being used
        from twisted.internet import reactor
        return reactor

    @inlineCallbacks
    def open_device(self, name, ok):
        if not ok:
            self._main_window.show()
            return

        if self.dut:
            self.dut.disconnect()
        self._main_window.show()
        dut = WSA(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)

        if hasattr(dut.properties, 'MINIMUM_FW_VERSION') and parse_version(
                dut.fw_version) < parse_version(dut.properties.MINIMUM_FW_VERSION):
            too_old = QtGui.QMessageBox()
            too_old.setText('Your device firmware version is {0}'
                ' but this application is expecting at least version'
                ' {1}. Some features may not work properly'.format(
                dut.fw_version, dut.properties.MINIMUM_FW_VERSION))
            too_old.exec_()
        if self._output_file:
            dut.set_capture_output(self._output_file)

        self.dut = dut
        self.plot_state = gui_config.PlotState(dut.properties)
        self.dut_prop = self.dut.properties
        self.sweep_dut = SweepDevice(dut, self.receive_sweep)
        self.cap_dut = CaptureDevice(dut, async_callback=self.receive_capture,
            device_settings=self.plot_state.dev_set)
        self._dev_group.configure(self.dut.properties)
        self.enable_controls()
        cu._select_center_freq(self)
        self._rbw_box.setCurrentIndex(3)
        self._plot.const_window.show()
        self._plot.iq_window.show()
        self.plot_state.enable_block_mode(self)
        self.read_block()

    def read_sweep(self):
        device_set = dict(self.plot_state.dev_set)
        device_set.pop('rfe_mode')
        device_set.pop('freq')
        device_set.pop('decimation')
        device_set.pop('fshift')
        device_set.pop('iq_output_path')
        self.sweep_dut.capture_power_spectrum(self.plot_state.fstart,
                                              self.plot_state.fstop,
                                              self.plot_state.rbw,
                                              device_set,
                                              mode=self._sweep_mode)

    def read_block(self):
        self.cap_dut.capture_time_domain(self.plot_state.rbw)


    def receive_capture(self, fstart, fstop, data):
        # store usable bins before next call to capture_time_domain
        self.usable_bins = list(self.cap_dut.usable_bins)
        self.sweep_segments = None

        if not self.plot_state.block_mode:
            self.read_sweep()
            return
        self.read_block()
        if 'reflevel' in data['context_pkt']:
            self.ref_level = data['context_pkt']['reflevel']

        self.pow_data = compute_fft(self.dut, data['data_pkt'], data['context_pkt'], ref = self.ref_level)
        self.raw_data = data['data_pkt']

        self.update_plot()

    def receive_sweep(self, fstart, fstop, data):
        self.sweep_segments = list(self.sweep_dut.sweep_segments)
        self.usable_bins = None
        if self.plot_state.block_mode:
            self.read_block()
            return
        self.read_sweep()

        if len(data) > 2:
            self.pow_data = data
        self.iq_data = None

        self.update_plot()


    def keyPressEvent(self, event):
        if self.dut:
            hotkey_util(self, event)
           
    def mousePressEvent(self, event):
        if self.dut:
            marker = self._plot.markers[self._marker_tab.currentIndex()]
            trace = self._plot.traces[marker.trace_index]
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                click_pos =  event.pos().x() - 68
                plot_window_width = self._plot.window.width() - 68

                if click_pos < plot_window_width and click_pos > 0:

                    window_freq = self._plot.view_box.viewRange()[0]
                    window_bw =  (window_freq[1] - window_freq[0])
                    click_freq = ((float(click_pos) / float(plot_window_width)) * float(window_bw)) + window_freq[0]
                    index = find_nearest_index(click_freq, trace.freq_range)
                    self._plot.markers[self._marker_tab.currentIndex()].data_index = index

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        for x in range(8):
            grid.setColumnMinimumWidth(x, 300)

        # add plot widget
        plot_width = 8

        grid.addWidget(self._plot_layout(),0,0,13,plot_width)

        self.marker_labels = []
        marker_label, delta_label, diff_label = self._marker_labels()
        self.marker_labels.append(marker_label)
        self.marker_labels.append(delta_label)
        grid.addWidget(marker_label, 0, 1, 1, 2)
        grid.addWidget(delta_label, 0, 3, 1, 2)
        grid.addWidget(diff_label , 0, 5, 1, 2)

        y = 0
        x = plot_width

        controls_layout = QtGui.QVBoxLayout()
        controls_layout.addWidget(self._trace_controls())
        controls_layout.addWidget(self._plot_controls())
        controls_layout.addWidget(self._device_controls())
        controls_layout.addWidget(self._freq_controls())
        controls_layout.addStretch()
        grid.addLayout(controls_layout, y, x, 13, 5)

        self._grid = grid
        self.update_freq()


        self.setLayout(grid)

    def _plot_layout(self):
        vsplit = QtGui.QSplitter()
        vsplit.setOrientation(QtCore.Qt.Vertical)
        vsplit.addWidget(self._plot.window)

        hsplit = QtGui.QSplitter()
        hsplit.addWidget(self._plot.const_window)
        hsplit.addWidget(self._plot.iq_window)
        self._plot.const_window.heightForWidth(1)
        self._plot.const_window.hide()
        self._plot.iq_window.hide()
        vsplit.addWidget(hsplit)

        self._plot_layout = vsplit
        return self._plot_layout

    def _trace_controls(self):
        trace_group = QtGui.QGroupBox("Traces")

        self._trace_group = trace_group

        trace_controls_layout = QtGui.QVBoxLayout()

        # first row will contain the tabs
        first_row = QtGui.QHBoxLayout()

        # add tabs for each trace
        trace_tab = QtGui.QTabBar()
        count = 0
        for (trace,(r,g,b)) in zip(labels.TRACES, colors.TRACE_COLORS):
            trace_tab.addTab(trace)
            color = QtGui.QColor()
            color.setRgb(r,g,b)
            pixmap = QtGui.QPixmap(10,10)
            pixmap.fill(color)
            icon = QtGui.QIcon(pixmap)
            trace_tab.setTabIcon(count,icon)
            count += 1

        self._trace_tab = trace_tab
        trace_tab.currentChanged.connect(lambda: cu._trace_tab_change(self))

        self.control_widgets.append(self._trace_tab)
        first_row.addWidget(trace_tab)

        # second row contains the tab attributes
        second_row = QtGui.QHBoxLayout()
        max_hold, min_hold, write, store, blank  = self._trace_items()
        second_row.addWidget(max_hold)
        second_row.addWidget(min_hold)
        second_row.addWidget(write)
        second_row.addWidget(blank)
        second_row.addWidget(store)
        trace_controls_layout.addLayout(first_row)
        trace_controls_layout.addLayout(second_row) 
        trace_group.setLayout(trace_controls_layout)
        return trace_group

    def _trace_items(self):

        trace_attr = {}
        store = QtGui.QCheckBox('Store')
        store.clicked.connect(lambda: cu._store_trace(self))
        store.setEnabled(False)
        trace_attr['store'] = store

        max_hold = QtGui.QRadioButton('Max Hold')
        max_hold.clicked.connect(lambda: cu._max_hold(self))
        trace_attr['max_hold'] = max_hold

        min_hold = QtGui.QRadioButton('Min Hold')
        min_hold.clicked.connect(lambda: cu._min_hold(self))
        trace_attr['min_hold'] = min_hold

        write = QtGui.QRadioButton('Write')
        write.clicked.connect(lambda: cu._trace_write(self))
        trace_attr['write'] = write

        blank = QtGui.QRadioButton('Blank')
        blank.clicked.connect(lambda: cu._blank_trace(self))
        trace_attr['blank'] = blank

        self._trace_attr = trace_attr
        self._trace_attr['write'].click()
        return max_hold, min_hold, write, store, blank

    def _device_controls(self):
        self._dev_group = DeviceControlsWidget()
        self._connect_device_controls()
        self.control_widgets.append(self._dev_group)
        return self._dev_group

    def _connect_device_controls(self):

        def new_antenna():
            self.plot_state.dev_set['antenna'] = (int(self._dev_group._antenna_box.currentText().split()[-1]))
            self.cap_dut.configure_device(self.plot_state.dev_set)
        
        def new_dec():
            self.plot_state.dev_set['decimation'] = int(
                self._dev_group._dec_box.currentText().split(' ')[-1])
            self.cap_dut.configure_device(self.plot_state.dev_set)
            self.update_freq()

        def new_freq_shift():
            rfe_mode = 'ZIF'
            prop = self.dut.properties
            max_fshift = prop.MAX_FSHIFT[rfe_mode]
            try:
                if float(self._dev_group._freq_shift_edit.text()) * M < max_fshift:
                    self.plot_state.dev_set['fshift'] = float(self._dev_group._freq_shift_edit.text()) * M
                else:
                    self._dev_group._freq_shift_edit.setText(str(self.plot_state.dev_set['fshift'] / M))
            except ValueError:
                self._dev_group._freq_shift_edit.setText(str(self.plot_state.dev_set['fshift'] / M))
                return
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_gain():
            self.plot_state.dev_set['gain'] = self._dev_group._gain_box.currentText().split()[-1].lower().encode('ascii')
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_ifgain():
            self.plot_state.dev_set['ifgain'] = self._dev_group._ifgain_box.value()
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_attenuator():
            self.plot_state.dev_set['attenuator'] = self._dev_group._attenuator_box.isChecked()
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_pll_reference():
            if 'INTERNAL' in str(self._dev_group._pll_box.currentText()):
                src = 'INT'
            else:
                src = 'EXT'
            self.plot_state.dev_set['pll_reference'] = src
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_iq_path():
            self.plot_state.dev_set['iq_output_path'] = str(self._dev_group._iq_output_box.currentText().split()[-1])
            
            if self.plot_state.dev_set['iq_output_path'] == 'CONNECTOR':
                # disable unwanted controls
                cu._external_digitizer_mode(self)
            else:
                cu._internal_digitizer_mode(self)
                self.cap_dut.configure_device(self.plot_state.dev_set)
                self.read_block()
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_input_mode():
            input_mode = self._dev_group._mode.currentText()
            if not input_mode:
                return
            if input_mode.startswith('Sweep '):

                self._plot.const_window.hide()
                self._plot.iq_window.hide()
                self.plot_state.dev_set['rfe_mode'] = str(input_mode.split(" ")[-1])
                cu._update_rbw_values(self)
                self.plot_state.disable_block_mode(self)
                self._rbw_box.setCurrentIndex(0)
                self._dev_group._dec_box.setEnabled(False)
                self._dev_group._freq_shift_edit.setEnabled(False)
                self._sweep_mode = input_mode.split(' ',1)[1]

                return

            self._plot.const_window.show()
            self._plot.iq_window.show()
            self.plot_state.enable_block_mode(self)

            self.plot_state.dev_set['rfe_mode'] = str(input_mode)
            cu._update_rbw_values(self)
            self.plot_state.bandwidth = self.dut_prop.FULL_BW[input_mode]
            if self.plot_state.dev_set['rfe_mode'] == 'IQIN':
                self._freq_edit.setText(str(self.dut_prop.MIN_TUNABLE[self.plot_state.dev_set['rfe_mode']]/M))

            self.plot_state.update_freq_set(
                fcenter=float(self._freq_edit.text()) * M)
            self._bw_edit.setText(str(float(self.dut.properties.FULL_BW[self.plot_state.dev_set['rfe_mode']])/ M) + '\n')
            self.cap_dut.configure_device(self.plot_state.dev_set)

            self._rbw_box.setCurrentIndex(4 if input_mode == 'SH' else 3)
            cu._center_plot_view(self)
            if input_mode == 'HDR':
                self._dev_group._dec_box.setEnabled(False)
                self._dev_group._freq_shift_edit.setEnabled(False)
            else:
                self._dev_group._dec_box.setEnabled(True)
                self._dev_group._freq_shift_edit.setEnabled(True)

        self._dev_group._antenna_box.currentIndexChanged.connect(new_antenna)
        self._dev_group._gain_box.currentIndexChanged.connect(new_gain)
        self._dev_group._dec_box.currentIndexChanged.connect(new_dec)
        self._dev_group._freq_shift_edit.returnPressed.connect(new_freq_shift) 
        self._dev_group._ifgain_box.valueChanged.connect(new_ifgain)
        self._dev_group._attenuator_box.clicked.connect(new_attenuator)
        self._dev_group._mode.currentIndexChanged.connect(new_input_mode)
        self._dev_group._iq_output_box.currentIndexChanged.connect(new_iq_path)
        self._dev_group._pll_box.currentIndexChanged.connect(new_pll_reference)

    def _trigger_control(self):
        trigger = QtGui.QCheckBox("Trigger")
        trigger.setToolTip("[T]\nTurn the Triggers on/off") 
        trigger.clicked.connect(lambda: cu._trigger_control(self))
        self._trigger = trigger
        self.control_widgets.append(self._trigger)
        return trigger

    def _attenuator_control(self):
        attenuator = QtGui.QCheckBox("Attenuator")
        attenuator.setChecked(True)
        def new_attenuator():
            self.plot_state.dev_set['attenuator'] = attenuator.isChecked()
        attenuator.clicked.connect(new_attenuator)
        self._attenuator_box = attenuator
        self.control_widgets.append(attenuator)
        return attenuator
    
    def _freq_controls(self):
        freq_group = QtGui.QGroupBox("Frequency Control")
        self._freq_group = freq_group

        freq_layout = QtGui.QVBoxLayout()

        fstart_hbox = QtGui.QHBoxLayout()
        fstart_bt, fstart_txt = self._fstart_controls()
        fstart_hbox.addWidget(fstart_bt)
        fstart_hbox.addWidget(fstart_txt)
        fstart_hbox.addWidget(QtGui.QLabel('MHz'))
        self._fstart_hbox = fstart_hbox

        cfreq_hbox = QtGui.QHBoxLayout()
        cfreq_bt, cfreq_txt = self._center_freq()
        cfreq_hbox.addWidget(cfreq_bt)
        cfreq_hbox.addWidget(cfreq_txt)
        cfreq_hbox.addWidget(QtGui.QLabel('MHz'))
        self._cfreq_hbox = cfreq_hbox

        bw_hbox = QtGui.QHBoxLayout()
        bw_bt, bw_txt = self._bw_controls()
        bw_hbox.addWidget(bw_bt)
        bw_hbox.addWidget(bw_txt)
        bw_hbox.addWidget(QtGui.QLabel('MHz'))
        self._bw_hbox = bw_hbox

        fstop_hbox = QtGui.QHBoxLayout()
        fstop_bt, fstop_txt = self._fstop_controls()
        fstop_hbox.addWidget(fstop_bt)
        fstop_hbox.addWidget(fstop_txt)
        fstop_hbox.addWidget(QtGui.QLabel('MHz'))
        self._fstop_hbox = fstop_hbox

        freq_inc_hbox = QtGui.QHBoxLayout()
        freq_inc_steps, freq_inc_plus, freq_inc_minus = self._freq_incr()
        freq_inc_hbox.addWidget(freq_inc_minus)
        freq_inc_hbox.addWidget(freq_inc_steps)
        freq_inc_hbox.addWidget(freq_inc_plus)
        self._freq_inc_hbox = freq_inc_hbox

        rbw_hbox = QtGui.QHBoxLayout()
        rbw = self._rbw_controls()
        rbw_hbox.addWidget(QtGui.QLabel('Resolution Bandwidth:'))
        rbw_hbox.addWidget(rbw)
        self._rbw_hbox = rbw_hbox
        
        freq_layout.addLayout(self._fstart_hbox)
        freq_layout.addLayout(self._cfreq_hbox)
        freq_layout.addLayout(self._bw_hbox)
        freq_layout.addLayout(self._fstop_hbox)
        freq_layout.addLayout(self._freq_inc_hbox)
        freq_layout.addLayout(self._rbw_hbox)
        freq_group.setLayout(freq_layout)
        self._freq_layout = freq_layout
        return freq_group

    def _center_freq(self):
        cfreq = QtGui.QPushButton('Center')
        cfreq.setToolTip("[2]\nTune the center frequency") 
        self._cfreq = cfreq
        cfreq.clicked.connect(lambda: cu._select_center_freq(self))
        freq_edit = QtGui.QLineEdit(str(gui_config.INIT_CENTER_FREQ / float(M)))
        self._freq_edit = freq_edit
        self.control_widgets.append(self._cfreq)
        self.control_widgets.append(self._freq_edit)
        def freq_change():
            cu._select_center_freq(self)
            self.update_freq()
            self.update_freq_edit()

        freq_edit.returnPressed.connect(lambda: freq_change())
        return cfreq, freq_edit

    def _freq_incr(self):
        steps = QtGui.QComboBox(self)
        steps.addItem("Adjust: 1 MHz")
        steps.addItem("Adjust: 2.5 MHz")
        steps.addItem("Adjust: 10 MHz")
        steps.addItem("Adjust: 25 MHz")
        steps.addItem("Adjust: 100 MHz")
        self.fstep = float(steps.currentText().split()[1])
        def freq_step_change():
            self.fstep = float(steps.currentText().split()[1])
        steps.currentIndexChanged.connect(freq_step_change)
        steps.setCurrentIndex(2)
        self._fstep_box = steps
        def freq_step(factor):
            try:
                f = float(self._freq_edit.text())
            except ValueError:
                return
            delta = float(steps.currentText().split()[1]) * factor
            self.update_freq(delta)
            self.update_freq_edit()   
        freq_minus = QtGui.QPushButton('-')
        freq_minus.clicked.connect(lambda: freq_step(-1))
        self._freq_minus = freq_minus
        freq_plus = QtGui.QPushButton('+')
        freq_plus.clicked.connect(lambda: freq_step(1))
        self._freq_plus = freq_plus
        self.control_widgets.append(self._freq_plus)
        self.control_widgets.append(self._freq_minus)
        self.control_widgets.append(self._fstep_box)
        return  steps, freq_plus, freq_minus

    def _bw_controls(self):
        bw = QtGui.QPushButton('Span')
        bw.setToolTip("[3]\nChange the bandwidth of the current plot")
        self._bw = bw
        bw.clicked.connect(lambda: cu._select_bw(self))
        bw_edit = QtGui.QLineEdit(str(gui_config.INIT_BANDWIDTH / float(M)))
        def freq_change():
            cu._select_bw(self)
            self.update_freq()
            self.update_freq_edit()   
        bw_edit.returnPressed.connect(lambda: freq_change())
        self._bw_edit = bw_edit
        self.control_widgets.append(self._bw_edit)
        self.control_widgets.append(self._bw)
        return bw, bw_edit

    def _fstart_controls(self):
        fstart = QtGui.QPushButton('Start')
        fstart.setToolTip("[1]\nTune the start frequency")
        self._fstart = fstart
        fstart.clicked.connect(lambda: cu._select_fstart(self))
        f = gui_config.INIT_CENTER_FREQ - (gui_config.INIT_BANDWIDTH / 2)
        freq = QtGui.QLineEdit(str(f / float(M)))
        def freq_change():
            cu._select_fstart(self)
            self.update_freq()
            self.update_freq_edit()

        freq.returnPressed.connect(lambda: freq_change())
        self._fstart_edit = freq
        self.control_widgets.append(self._fstart)
        self.control_widgets.append(self._fstart_edit)
        return fstart, freq

    def _fstop_controls(self):
        fstop = QtGui.QPushButton('Stop')
        fstop.setToolTip("[4]Tune the stop frequency") 
        self._fstop = fstop
        fstop.clicked.connect(lambda: cu._select_fstop(self))
        f = gui_config.INIT_CENTER_FREQ + (gui_config.INIT_BANDWIDTH / 2)
        freq = QtGui.QLineEdit(str(f / float(M)))
        def freq_change():
            cu._select_fstop(self)   
            self.update_freq()
            self.update_freq_edit()            
        freq.returnPressed.connect(lambda: freq_change())
        self._fstop_edit = freq
        self.control_widgets.append(self._fstop)
        self.control_widgets.append(self._fstop_edit)
        return fstop, freq

    def _rbw_controls(self):
        rbw = QtGui.QComboBox(self)
        rbw.setToolTip("Change the RBW of the FFT plot")
        self._points_values = RBW_VALUES
        self._hdr_points_values = HDR_RBW_VALUES
        self._rbw_box = rbw
        rbw.addItems([str(p) + ' KHz' for p in self._points_values])

        def new_rbw():
        
            if not self.plot_state.dev_set['rfe_mode'] == 'HDR':    
                self.plot_state.update_freq_set(rbw = 1e3 * self._points_values[rbw.currentIndex()])
            else:
                self.plot_state.update_freq_set(rbw = self._hdr_points_values[rbw.currentIndex()])

        rbw.setCurrentIndex(0)
        rbw.currentIndexChanged.connect(new_rbw)
        self.control_widgets.append(self._rbw_box)
        return rbw

    def update_freq(self, delta=None):
        if not self.dut:
            return
        prop = self.dut.properties
        rfe_mode = self.plot_state.dev_set['rfe_mode']
        min_tunable = prop.MIN_TUNABLE[rfe_mode]
        max_tunable = prop.MAX_TUNABLE[rfe_mode]
        if delta == None:
            delta = 0    
        try:
            if self.plot_state.freq_sel == 'CENT':
                f = (float(self._freq_edit.text()) + delta) * M
                if f > max_tunable or f < min_tunable:
                    return
                self.plot_state.update_freq_set(fcenter = f)
                self.cap_dut.configure_device(self.plot_state.dev_set)
            elif self.plot_state.freq_sel == 'FSTART':
                f = (float(self._fstart_edit.text()) + delta) * M
                if f > max_tunable or f <min_tunable or f > self.plot_state.fstop:
                    return
                self.plot_state.update_freq_set(fstart = f)
            
            elif self.plot_state.freq_sel == 'FSTOP': 
                f = (float(self._fstop_edit.text()) + delta) * M

                if f > max_tunable or f < min_tunable or f < self.plot_state.fstart:
                    return
                self.plot_state.update_freq_set(fstop = f)
            
            elif self.plot_state.freq_sel == 'BW':
                f = (float(self._bw_edit.text()) + delta) * M
                if f < 0:
                    return
                self.plot_state.update_freq_set(bw = f)
            for trace in self._plot.traces:
                try:
                    trace.data = self.pow_data
                except AttributeError:
                    break

        except ValueError:
            return
        if self.plot_state.trig:
            freq_region = self._plot.freqtrig_lines.getRegion()
            if (freq_region[0] < self.plot_state.fstart and freq_region[1] < self.plot_state.fstart) or (freq_region[0] > self.plot_state.fstop and freq_region[1] > self.plot_state.fstop):
                self._plot.freqtrig_lines.setRegion([self.plot_state.fstart,self.plot_state. fstop]) 

    def update_freq_edit(self):
        self._fstop_edit.setText("%0.1f" % (self.plot_state.fstop/ 1e6))
        self._fstart_edit.setText("%0.1f" % (self.plot_state.fstart/ 1e6))
        self._freq_edit.setText("%0.1f" % (self.plot_state.center_freq / 1e6))
        self._bw_edit.setText("%0.1f" % (self.plot_state.bandwidth / 1e6))
        self._center_bt.click()

    def _plot_controls(self):

        plot_group = QtGui.QGroupBox("Plot Control")
        self._plot_group = plot_group
        
        plot_controls_layout = QtGui.QVBoxLayout()
        
        first_row = QtGui.QHBoxLayout()
        marker_tab = QtGui.QTabBar()
        for marker in labels.MARKERS:
            marker_tab.addTab(marker)
        marker_tab.currentChanged.connect(lambda: cu._marker_tab_change(self))
        first_row.addWidget(marker_tab)
        
        self._marker_tab = marker_tab
        self.control_widgets.append(self._marker_tab)
        marker_check, marker_trace = self._marker_control()
        
        second_row = QtGui.QHBoxLayout()
        second_row.addWidget(marker_trace)
        second_row.addWidget(marker_check)
                
        third_row = QtGui.QHBoxLayout()
        third_row.addWidget(self._peak_control())
        third_row.addWidget(self._center_control())
        
        fourth_row = QtGui.QHBoxLayout()
        ref_level, ref_label, min_level, min_label = self._ref_controls()
        
        fourth_row.addWidget(ref_label)
        fourth_row.addWidget(ref_level)
        fourth_row.addWidget(min_label)
        fourth_row.addWidget(min_level)

        plot_controls_layout.addLayout(first_row)
        plot_controls_layout.addLayout(second_row)
        plot_controls_layout.addLayout(third_row)
        plot_controls_layout.addLayout(fourth_row)
        plot_group.setLayout(plot_controls_layout)
        
        return plot_group
        
    def _marker_control(self):
        marker_trace = QtGui.QComboBox()
        marker_trace.setEnabled(False)
        marker_trace.setMaximumWidth(50)
        marker_trace.currentIndexChanged.connect(lambda: cu._marker_trace_control(self))
        update_marker_traces(marker_trace, self._plot.traces)
        
        self._marker_trace = marker_trace
        marker_check = QtGui.QCheckBox('Enabled')
        marker_check.clicked.connect(lambda: cu._marker_control(self))
        self._marker_check = marker_check

        self.control_widgets.append(self._marker_check)
        return marker_check,marker_trace
            
    def _peak_control(self):
        peak = QtGui.QPushButton('Peak')
        peak.setToolTip("[P]\nFind peak of the selected spectrum") 
        peak.clicked.connect(lambda: cu._find_peak(self))
        self._peak = peak
        self.control_widgets.append(self._peak)
        return peak
                
    def _center_control(self):
        center = QtGui.QPushButton('Recenter')
        center.setToolTip("[C]\nCenter the Plot View around the available spectrum") 
        center.clicked.connect(lambda: cu._center_plot_view(self))
        self._center_bt = center
        self.control_widgets.append(self._center_bt)
        return center
    
    def _ref_controls(self):
        ref_level = QtGui.QLineEdit(str(PLOT_YMAX))
        ref_level.returnPressed.connect(lambda: cu._change_ref_level(self))
        self._ref_level = ref_level
        self.control_widgets.append(self._ref_level)
        ref_label = QtGui.QLabel('Reference Level: ')
        
        min_level = QtGui.QLineEdit(str(PLOT_YMIN)) 
        min_level.returnPressed.connect(lambda: cu._change_min_level(self))
        min_label = QtGui.QLabel('Minimum Level: ')
        self._min_level = min_level
        self.control_widgets.append(self._min_level)
        return ref_level, ref_label, min_level, min_label

    def _marker_labels(self):
        marker_label = QtGui.QLabel('')
        marker_label.setStyleSheet('color: %s;' % colors.TEAL)
        marker_label.setMinimumHeight(25)
        
        delta_label = QtGui.QLabel('')
        delta_label.setStyleSheet('color: %s;' % colors.TEAL)
        delta_label.setMinimumHeight(25)
        
        diff_label = QtGui.QLabel('')
        diff_label.setStyleSheet('color: %s;' % colors.WHITE)
        diff_label.setMinimumHeight(25)
        self._diff_lab = diff_label
        return marker_label,delta_label, diff_label
       
    def update_plot(self):
       
        self.plot_state.update_freq_range(self.plot_state.fstart,
                                              self.plot_state.fstop, 
                                              len(self.pow_data))
        self.update_trace()
        self.update_iq()
        self.update_marker()
        self.update_diff()

    def update_trace(self):
        for trace in self._plot.traces:
            trace.update_curve(
                self.plot_state.freq_range,
                self.pow_data,
                self.usable_bins,
                self.sweep_segments)


    def update_iq(self):

        if self.raw_data.stream_id == VRT_IFDATA_I14Q14:    
            data = self.raw_data.data.numpy_array()
            i_data = np.array(data[:,0], dtype=float)/ZIF_BITS
            q_data = np.array(data[:,1], dtype=float)/ZIF_BITS
            self._plot.i_curve.setData(i_data)
            self._plot.q_curve.setData(q_data)
            self._plot.const_plot.clear()
            self._plot.const_plot.addPoints(
                x = i_data[0:CONST_POINTS],
                y = q_data[0:CONST_POINTS],
                symbol = 'o',
                size = 1, pen = 'y',
                brush = 'y')
        
        else:
            data = self.raw_data.data.numpy_array()
            i_data = np.array(data, dtype=float)
            if self.raw_data.stream_id == VRT_IFDATA_I14:
                i_data = i_data /ZIF_BITS
            self._plot.i_curve.setData(i_data)
            
            self._plot.q_curve.clear()
            self._plot.const_plot.clear()
            
    
    def update_trig(self):
            if self.plot_state.trig_set:
                freq_region = self._plot.freqtrig_lines.getRegion()
                self.plot_state.trig_set = TriggerSettings(TRIGGER_TYPE_LEVEL,
                                                        min(freq_region), 
                                                        max(freq_region),
                                                        self._plot.amptrig_line.value())

                self.dut.trigger(self.plot_state.trig_set)
    def update_marker(self):        
            
            for marker, marker_label in zip(self._plot.markers, self.marker_labels):
                if marker.enabled:
                    trace = self._plot.traces[marker.trace_index]

                    if not trace.blank:
                        marker_label.setStyleSheet('color: rgb(%s, %s, %s);' % (trace.color[0],
                                                                             trace.color[1],
                                                                            trace.color[2]))
                        
                        marker.update_pos(trace.freq_range, trace.data)
                        marker_text = 'Frequency: %0.2f MHz \n Power %0.2f dBm' % (trace.freq_range[marker.data_index]/1e6, 
                                                                                   trace.data[marker.data_index])
                        marker_label.setText(marker_text)

                else:
                    marker_label.setText('')

    def update_diff(self):

        num_markers = 0
        traces = []
        data_indices = []
        for marker in self._plot.markers:

            if marker.enabled == True:
                num_markers += 1
                traces.append(self._plot.traces[marker.trace_index])
                data_indices.append(marker.data_index)
                
        if num_markers == len(labels.MARKERS):
            freq_diff = np.abs((traces[0].freq_range[data_indices[0]]/1e6) - (traces[1].freq_range[data_indices[1]]/1e6))
            
            power_diff = np.abs((traces[0].data[data_indices[0]]) - (traces[1].data[data_indices[1]]))
            
            delta_text = 'Delta : %0.1f MHz \nDelta %0.2f dBm' % (freq_diff, power_diff )
            self._diff_lab.setText(delta_text)
        else:
            self._diff_lab.setText('')

    def enable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(True)
            
        
        for key in self._trace_attr:
            self._trace_attr[key].setEnabled(True)
        
    def disable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(False)
            
        for key in self._trace_attr:
            self._trace_attr[key].setEnabled(False)

        
