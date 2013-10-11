
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
import time
import math
from contextlib import contextmanager
from util import find_max_index, find_nearest_index
from util import hotkey_util, update_marker_traces
from pyrf.gui import colors
from pyrf.gui import labels
import control_util as cu
from plot_widget import Plot
from pyrf.gui import gui_config
from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.config import TriggerSettings, TRIGGER_TYPE_LEVEL
from pyrf.capture_device import CaptureDevice
from pyrf.units import M
from pyrf.numpy_util import compute_fft

RBW_VALUES = [976.562, 488.281, 244.141, 122.070, 61.035, 30.518, 15.259, 7.629, 3.815]
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
    def __init__(self, name=None):
        super(MainWindow, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        WINDOW_WIDTH = screen.width() * 0.7
        WINDOW_HEIGHT = screen.height() * 0.6
        self.resize(WINDOW_WIDTH,WINDOW_HEIGHT)
        self.initUI()


        self.show()
    
    def initUI(self):
        name = None
        if len(sys.argv) > 1:
            name = sys.argv[1]
        self.mainPanel = MainPanel()
        openAction = QtGui.QAction('&Open Device', self)
        openAction.triggered.connect( self.mainPanel.open_device_dialog)
        exitAction = QtGui.QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)
        self.setWindowTitle('Spectrum Analyzer')
        self.setCentralWidget(self.mainPanel)
        self.mainPanel.show()
        if name:
            self.mainPanel.open_device(name)
        else:
            self.mainPanel.open_device_dialog()
    
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
    def __init__(self):
        self.dut = None
        self.control_widgets = []
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

        self._reactor = self._get_reactor()

    def _get_reactor(self):
        # late import because installReactor is being used
        from twisted.internet import reactor
        return reactor

    def open_device_dialog(self):
        name, ok = QtGui.QInputDialog.getText(self, 'Open Device',
            'Enter a hostname or IP address:')
        while True:
            if not ok:
                return
            try:
                self.open_device(name)
                break
            except socket.error:
                name, ok = QtGui.QInputDialog.getText(self, 'Open Device',
                    'Connection Failed, please try again\n\n'
                    'Enter a hostname or IP address:')

    @inlineCallbacks
    def open_device(self, name):
        dut = WSA(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)
        self.dut = dut
        self.plot_state = gui_config.PlotState(dut.properties)
        self.dut_prop = self.dut.properties
        if self.dut_prop.model == 'WSA5000':
            self._antenna_box.hide()
            self._gain_box.hide()
            self._trigger.hide()
            self._attenuator_box.show()
        else:
            self._antenna_box.show()
            self._gain_box.show()
            self._trigger.show()
            self._attenuator_box.hide()
        self.label = QtGui.QLabel('HELLO')
        self.sweep_dut = SweepDevice(dut, self.receive_data)
        self.cap_dut = CaptureDevice(dut, self.receive_data)
        self.enable_controls()
        cu._select_fstart(self)
        self.read_sweep()

    def read_sweep(self):
        #TODO: find cleaner way to do this
        self.plot_state.dev_set.pop('freq', None)
        self.plot_state.dev_set.pop('trigger', None)
        self.sweep_dut.capture_power_spectrum(self.plot_state.fstart,
                                              self.plot_state.fstop,
                                              self.plot_state.rbw,
                                              self.plot_state.dev_set,
                                              continuous = False)

    def read_trigg(self):
        device_set = self.plot_state.dev_set
        #TODO: find cleaner way to do this
        device_set['freq'] = self.plot_state.center_freq
        device_set['trigger'] = self.plot_state.trig_set

        self.cap_dut.capture_time_domain(device_set,self.plot_state.rbw)


    def receive_data(self, fstart, fstop, data):
        if not self.plot_state.enable_plot:
            return
        if self.plot_state.trig_set:
            self.read_trigg()
            if not len(data) > 5:
                pow_ = compute_fft(self.dut, data['data_pkt'], data['context_pkt'])

                attenuated_edge = math.ceil((1.0 -
                float(self.dut_prop.USABLE_BW) / self.dut_prop.FULL_BW) / 2 * len(pow_))
                self.pow_data = pow_[attenuated_edge:-attenuated_edge]
                self.iq_data = data['data_pkt']
        else:
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
            trace = self._plot.traces[self._marker_trace.currentIndex()]
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                click_pos =  event.pos().x() - 68
                plot_window_width = self._plot.window.width() - 68

                if click_pos < plot_window_width and click_pos > 0:

                    window_freq = self._plot.view_box.viewRange()[0]
                    window_bw =  (window_freq[1] - window_freq[0])
                    click_freq = ((float(click_pos) / float(plot_window_width)) * float(window_bw)) + window_freq[0]
                    index = find_nearest_index(click_freq, trace.freq_range)
                    self._plot.markers[self._marker_tab.currentIndex()].data_index = index
                    # self.update_diff()
    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        for x in range(8):
            grid.setColumnMinimumWidth(x, 300)
        grid.setRowMinimumHeight(14, 800)
        
        # add plot widget
        plot_width = 8
        
        grid.addLayout(self._plot_layout(),0,0,15,plot_width)
        
        self.marker_labels = []
        marker_label, delta_label, diff_label = self._marker_labels()
        self.marker_labels.append(marker_label)
        self.marker_labels.append(delta_label)
        grid.addWidget(marker_label, 0, 1, 1, 2)
        grid.addWidget(delta_label, 0, 3, 1, 2)
        grid.addWidget(diff_label , 0, 5, 1, 2)
 
        y = 0
        x = plot_width

        grid.addWidget(self._trace_controls(), y, x, 2, 5)
        y += 2
        grid.addWidget(self._plot_controls(), y, x, 4, 5)
        y += 5
        grid.addWidget(self._device_controls(), y, x, 2, 5)
        y += 2
        grid.addWidget(self._freq_controls(), y, x, 4, 5)

        self._grid = grid
        self.update_freq()


        self.setLayout(grid)
        # self._second_row.removeWidget(self._plot.const_window)
        # self._plot_layout.removeWidget(self._plot.const_window)
    def _plot_layout(self):
        plot_layout =  QtGui.QGridLayout()
        plot_layout.setSpacing(10)
        plot_layout.addWidget(self._plot.window,0,0,1,5)

        plot_layout.addWidget(self._plot.const_window,1,0)
        plot_layout.addWidget(self._plot.iq_window,1,2)
        self._plot.const_window.hide()
        self._plot.iq_window.hide()


        self._plot_layout = plot_layout
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
        dev_group = QtGui.QGroupBox("Device Control")
        dev_group.setMaximumWidth(300)
        self.dev_group = dev_group
        
        dev_layout = QtGui.QVBoxLayout()
        
        first_row = QtGui.QHBoxLayout()
        first_row.addWidget(self._antenna_control())
        first_row.addWidget(self._trigger_control())
        first_row.addWidget(self._attenuator_control())
        
        second_row = QtGui.QHBoxLayout()
        second_row.addWidget(self._gain_control())
        second_row.addWidget(self._ifgain_control())
        
        dev_layout.addLayout(first_row)
        dev_layout.addLayout(second_row)

        dev_group.setLayout(dev_layout)         
        return dev_group
    
    def _antenna_control(self):
        antenna = QtGui.QComboBox(self)
        antenna.setToolTip("Choose Antenna") 
        antenna.addItem("Antenna 1")
        antenna.addItem("Antenna 2")
        self._antenna_box = antenna
        self.control_widgets.append(self._antenna_box)
        def new_antenna():
            self.plot_state.dev_set['antenna'] = (int(antenna.currentText().split()[-1]))
        
        antenna.currentIndexChanged.connect(new_antenna)
        return antenna

    def _gain_control(self):
        gain = QtGui.QComboBox(self)
        gain.setToolTip("Choose RF Gain setting") 
        gain_values = ['VLow', 'Low', 'Med', 'High']
        for g in gain_values:
            gain.addItem("RF Gain: %s" % g)
        self._gain_values = [g.lower() for g in gain_values]
        self._gain_box = gain
        self.control_widgets.append(self._gain_box)
        def new_gain():
            self.plot_state.dev_set['gain'] = gain.currentText().split()[-1].lower().encode('ascii')
        gain.currentIndexChanged.connect(new_gain)
        return gain

    def _ifgain_control(self):
        ifgain = QtGui.QSpinBox(self)
        ifgain.setToolTip("Choose IF Gain setting")
        ifgain.setRange(-10, 25)
        ifgain.setSuffix(" dB")
        self._ifgain_box = ifgain
        self.control_widgets.append(self._ifgain_box)
        def new_ifgain():
            self.plot_state.dev_set['ifgain'] = ifgain.value()
        ifgain.valueChanged.connect(new_ifgain)
        return ifgain
    
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
        freq_group.setMaximumWidth(300)
        self._freq_group = freq_group
        
        freq_layout = QtGui.QVBoxLayout()
        
        fstart_hbox = QtGui.QHBoxLayout()
        fstart_bt, fstart_txt = self._fstart_controls()
        fstart_hbox.addWidget(fstart_bt)
        fstart_hbox.addWidget(fstart_txt)
        fstart_hbox.addWidget(QtGui.QLabel('MHz'))
        
        cfreq_hbox = QtGui.QHBoxLayout()
        cfreq_bt, cfreq_txt = self._center_freq()
        cfreq_hbox.addWidget(cfreq_bt)
        cfreq_hbox.addWidget(cfreq_txt)
        cfreq_hbox.addWidget(QtGui.QLabel('MHz'))
        
        bw_hbox = QtGui.QHBoxLayout()
        bw_bt, bw_txt = self._bw_controls()
        bw_hbox.addWidget(bw_bt)
        bw_hbox.addWidget(bw_txt)
        bw_hbox.addWidget(QtGui.QLabel('MHz'))
        
        fstop_hbox = QtGui.QHBoxLayout()
        fstop_bt, fstop_txt = self._fstop_controls()
        fstop_hbox.addWidget(fstop_bt)
        fstop_hbox.addWidget(fstop_txt)
        fstop_hbox.addWidget(QtGui.QLabel('MHz'))
        
        freq_inc_hbox = QtGui.QHBoxLayout()
        freq_inc_steps, freq_inc_plus, freq_inc_minus = self._freq_incr()
        freq_inc_hbox.addWidget(freq_inc_minus)
        freq_inc_hbox.addWidget(freq_inc_steps)
        freq_inc_hbox.addWidget(freq_inc_plus)
        
        rbw_hbox = QtGui.QHBoxLayout()
        rbw = self._rbw_controls()
        rbw_hbox.addWidget(QtGui.QLabel('Resolution Bandwidth:'))
        rbw_hbox.addWidget(rbw)
        
        freq_layout.addLayout(fstart_hbox)
        freq_layout.addLayout(cfreq_hbox)
        freq_layout.addLayout(bw_hbox)
        freq_layout.addLayout(fstop_hbox)
        freq_layout.addLayout(freq_inc_hbox)
        freq_layout.addLayout(rbw_hbox)
        freq_group.setLayout(freq_layout)
        
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
        f = gui_config.INIT_CENTER_FREQ - (gui_config.INIT_BANDWIDTH / 2)
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
        self._rbw_box = rbw
        rbw.addItems([str(p) + ' KHz' for p in self._points_values])
        def new_rbw():
            self.plot_state.update_freq_set(rbw = self._points_values[rbw.currentIndex()])
        rbw.setCurrentIndex(0)
        rbw.currentIndexChanged.connect(new_rbw)
        self.control_widgets.append(self._rbw_box)
        return rbw

    def update_freq(self, delta=None):
        if not self.dut:
            return
        prop = self.dut.properties

        if delta == None:
            delta = 0    
        try:
            if self.plot_state.freq_sel == 'CENT':
                f = (float(self._freq_edit.text()) + delta) * M
                if f > prop.MAX_TUNABLE or f < prop.MIN_TUNABLE:
                    return
                self.plot_state.update_freq_set(fcenter = f)
            
            elif self.plot_state.freq_sel == 'FSTART':
                f = (float(self._fstart_edit.text()) + delta) * M
                if f > prop.MAX_TUNABLE or f < prop.MIN_TUNABLE or f > self.plot_state.fstop:
                    return
                self.plot_state.update_freq_set(fstart = f)
            
            elif self.plot_state.freq_sel == 'FSTOP': 
                f = (float(self._fstop_edit.text()) + delta) * M
                if f > prop.MAX_TUNABLE or f < prop.MIN_TUNABLE or f < self.plot_state.fstart:
                    return
                self.plot_state.update_freq_set(fstop = f)
            
            elif self.plot_state.freq_sel == 'BW':
                f = (float(self._bw_edit.text()) + delta) * M
                if f < 0:
                    return
                self.plot_state.update_freq_set(bw = f)
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
        plot_group.setMaximumWidth(300)
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
        
        fifth_row = QtGui.QHBoxLayout()
        iq_checkbox =  self._iq_plot_controls() 
        fifth_row.addWidget(iq_checkbox)

        
        plot_controls_layout.addLayout(first_row)
        plot_controls_layout.addLayout(second_row)
        plot_controls_layout.addLayout(third_row)
        plot_controls_layout.addLayout(fourth_row)
        plot_controls_layout.addLayout(fifth_row)
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
    
    def _iq_plot_controls(self):
        iq_plot_checkbox = QtGui.QCheckBox('IQ Plot')
        iq_plot_checkbox.clicked.connect(lambda: cu._iq_plot_control(self))
        self._iq_plot_checkbox = iq_plot_checkbox
        self.control_widgets.append(self._iq_plot_checkbox)
        
        return iq_plot_checkbox
        
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
                                              self.plot_state.fstop , 
                                              len(self.pow_data))
        self.update_trace()
        self.update_iq()
        self.update_marker()
        self.update_diff()

    def update_trace(self):
        for trace in self._plot.traces:
            trace.update_curve(self.plot_state.freq_range, self.pow_data)


    def update_iq(self):
        if self.plot_state.block_mode:
                if self.iq_data:
                    data = self.iq_data.data.numpy_array()
                    i_data = np.array(data[:,0], dtype=float)/ZIF_BITS
                    q_data = np.array(data[:,1], dtype=float)/ZIF_BITS
                    self._plot.i_curve.setData(i_data)
                    self._plot.q_curve.setData(q_data)
                    self._plot.const_plot.clear()
                    self._plot.const_plot.addPoints(x = i_data[0:CONST_POINTS], 
                                               y = q_data[0:CONST_POINTS], 
                                                symbol = 'o', 
                                                size = 1, pen = 'y', 
                                                brush = 'y')
                                                
    def update_trig(self):
            if self.plot_state.trig_set:
                freq_region = self._plot.freqtrig_lines.getRegion()
                self.plot_state.trig_set = TriggerSettings(TRIGGER_TYPE_LEVEL,
                                                        min(freq_region), 
                                                        max(freq_region),
                                                        self._plot.amptrig_line.value())

    
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

        
