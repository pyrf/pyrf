"""
The main application window and GUI controls

``MainWindow`` creates and handles the ``File | Open Device`` menu and
wraps the ``MainPanel`` widget responsible for most of the interface.

All the buttons and controls and their callback functions are built in
``MainPanel`` and arranged on a grid.  A ``Pyqtgraph Window`` is created
and placed to left of the controls.
"""

from PySide import QtGui, QtCore
import numpy as np
import math

from contextlib import contextmanager
from pkg_resources import parse_version

from pyrf.gui import colors
from pyrf.gui import labels
from pyrf.gui import gui_config
from pyrf.gui.controller import SpecAController

from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.config import TriggerSettings, TRIGGER_TYPE_LEVEL
from pyrf.units import M
from pyrf.devices.thinkrf import WSA
from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)

from util import find_max_index, find_nearest_index
from util import hotkey_util, update_marker_traces
import control_util as cu
from plot_widget import Plot
from device_controls import DeviceControls
from frequency_controls import FrequencyControls
from discovery_widget import DiscoveryWidget
from trace_controls import TraceControls

PLOT_YMIN = -140
PLOT_YMAX = 0

DSP_OPTIONS = [
    ('&IQ Offset Correction', 'correct_phase', True),
    ('&DC Offset', 'hide_differential_dc_offset', True),
    ('&Convert to dBm', 'convert_to_dbm', True),
    ('Apply &Spectral Inversion', 'apply_spec_inv', True),
    ('Apply &Hanning Window', 'apply_window', True),
    ]

DEVELOPER_OPTIONS = [
    ('&Manual RFE Mode Selection', 'manual_rfe_mode', False),
    ('Show &Attenuated Edges', 'show_attenuated_edges', False),
    ('Show &Sweep Steps', 'show_sweep_steps', False),
    ]

# FIXME: we shouldn't be calculating fft in this module
ZIF_BITS = 2**13
CONST_POINTS = 512

# FIXME: calculate from device properties instead
IQ_PLOT_YMIN = {'ZIF': -1, 'HDR': -1, 'SH': -1, 'SHN': -1, 'IQIN': -1, 'DD': -1}
IQ_PLOT_YMAX = {'ZIF': 1, 'HDR': 1, 'SH': -1, 'SHN': -1, 'IQIN': 1, 'DD': 1}

try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass


class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, dut_address=None, playback_filename=None):
        super(MainWindow, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        WINDOW_WIDTH = screen.width() * 0.7
        WINDOW_HEIGHT = screen.height() * 0.6
        self.resize(WINDOW_WIDTH,WINDOW_HEIGHT)

        self.controller = SpecAController()
        self.init_menu_bar()
        self.initUI(dut_address, playback_filename)

    def initUI(self, dut_address, playback_filename):
        self.mainPanel = MainPanel(self.controller, self)

        self.setWindowTitle('Spectrum Analyzer')
        self.setCentralWidget(self.mainPanel)
        if dut_address:
            self.open_device(dut_address, True)
        elif playback_filename:
            self.start_playback(playback_filename)
        else:
            self.open_device_dialog()

    def init_menu_bar(self):
        open_action = QtGui.QAction('&Open Device', self)
        open_action.triggered.connect(self.open_device_dialog)
        play_action = QtGui.QAction('&Playback Recording', self)
        play_action.triggered.connect(self.open_playback_dialog)
        self.record_action = QtGui.QAction('Start &Recording', self)
        self.record_action.triggered.connect(self.start_recording)
        self.record_action.setDisabled(True)
        self.stop_action = QtGui.QAction('&Stop Recording', self)
        self.stop_action.triggered.connect(self.stop_recording)
        self.stop_action.setDisabled(True)
        exit_action = QtGui.QAction('&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(open_action)
        file_menu.addAction(play_action)
        file_menu.addSeparator()
        file_menu.addAction(self.record_action)
        file_menu.addAction(self.stop_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        def checkbox_action(apply_fn, text, option, default):
            action = QtGui.QAction(text, self)
            action.setCheckable(True)
            if default:
                action.toggle()
            action.triggered.connect(lambda:
                apply_fn(**{option: action.isChecked()}))
            return action

        self.dsp_menu = menubar.addMenu('&DSP Options')
        for text, option, default in DSP_OPTIONS:
            self.dsp_menu.addAction(checkbox_action(
                self.controller.apply_dsp_options, text, option, default))
        self.controller.apply_dsp_options(**dict((option, default)
            for text, option, default in DSP_OPTIONS))

        self.developer_menu = menubar.addMenu('D&eveloper Options')
        for text, option, default in DEVELOPER_OPTIONS:
            self.developer_menu.addAction(checkbox_action(
                self.controller.apply_developer_options, text, option, default))
        self.controller.apply_developer_options(**dict((option, default)
            for text, option, default in DEVELOPER_OPTIONS))

    def start_recording(self):
        self.stop_action.setDisabled(False)
        self.controller.start_recording()

    def stop_recording(self):
        self.stop_action.setDisabled(True)
        self.controller.stop_recording()

    def open_device_dialog(self):
        self.discovery_widget = DiscoveryWidget(
            open_device_callback=self.open_device,
            name="Open Device")
        self.discovery_widget.show()

    def open_playback_dialog(self):
        self.controller.set_device(None)
        playback_filename, file_type = QtGui.QFileDialog.getOpenFileName(self,
            "Play Recording", None, "VRT Packet Capture Files (*.vrt)")
        if playback_filename:
            self.start_playback(playback_filename)

    def start_playback(self, playback_filename):
        self.record_action.setDisabled(True)
        self.stop_action.setDisabled(True)
        self.controller.set_device(playback_filename=playback_filename)
        self.show()

    @inlineCallbacks
    def open_device(self, name, ok):
        if not ok:
            self.show()
            return

        self.show()
        dut = WSA(connector=TwistedConnector(self._get_reactor()))
        yield dut.connect(name)
        self.setWindowTitle('Spectrum Analyzer Connected To: %s' %name)
        if hasattr(dut.properties, 'MINIMUM_FW_VERSION') and parse_version(
                dut.fw_version) < parse_version(dut.properties.MINIMUM_FW_VERSION):
            too_old = QtGui.QMessageBox()
            too_old.setText('Your device firmware version is {0}'
                ' but this application is expecting at least version'
                ' {1}. Some features may not work properly'.format(
                dut.fw_version, dut.properties.MINIMUM_FW_VERSION))
            too_old.exec_()
        self.controller.set_device(dut)
        self.record_action.setDisabled(False)
        self.stop_action.setDisabled(True)

    def closeEvent(self, event):
        event.accept()
        self.controller.stop_recording()
        self.controller.set_device()
        self._get_reactor().stop()

    def _get_reactor(self):
        # late import because installReactor is being used
        from twisted.internet import reactor
        return reactor

class MainPanel(QtGui.QWidget):
    """
    The spectrum view and controls
    """
    def __init__(self, controller,  main_window):
        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)
        controller.capture_receive.connect(self.capture_received)

        self._main_window = main_window

        self.ref_level = 0
        self.dut = None
        self.control_widgets = []
        super(MainPanel, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        self.setMinimumWidth(screen.width() * 0.7)
        self.setMinimumHeight(screen.height() * 0.6)
        self.plot_state = None
        # plot window
        self._plot = Plot(controller, self)
        self._marker_trace = None
        self._vrt_context = {}
        self.initUI()
        self.disable_controls()
        self.ref_level = 0
        self.plot_state = None

        self.freq_range = None, None

    def device_changed(self, dut):
        self.plot_state = gui_config.PlotState(dut.properties)
        self.dut_prop = dut.properties

        self.enable_controls()
        self._plot.const_window.show()
        self._plot.iq_window.show()

    def state_changed(self, state, changed):
        """
        signal handler for speca state changes
        :param state: new SpecAState object
        :param changed: list of attribute names changed
        """
        self.gui_state = state

        if 'mode' in changed:
            self.rfe_mode = state.rfe_mode()  # used by recentering code
            if state.sweeping():
                self.cf_marker.setEnabled(True)
                self._plot.const_window.hide()
                self._plot.iq_window.hide()
                return
            self.cf_marker.setEnabled(False)
            self._plot.const_window.show()
            self._plot.iq_window.show()

            if self.rfe_mode in ('DD', 'IQIN'):
                freq = self.dut_prop.MIN_TUNABLE[self.rfe_mode]
                full_bw = self.dut_prop.FULL_BW[self.rfe_mode]

                self._plot.center_view(freq, full_bw, self.plot_state.min_level, self.plot_state.ref_level)
                self._plot.iq_window.setYRange(IQ_PLOT_YMIN[self.rfe_mode],
                                        IQ_PLOT_YMAX[self.rfe_mode])
            else:
                freq = state.center
                full_bw = state.span

                self._plot.center_view(freq - full_bw/2, freq + full_bw/2, self.plot_state.min_level, self.plot_state.ref_level)
                self._plot.iq_window.setYRange(IQ_PLOT_YMIN[self.rfe_mode],
                                        IQ_PLOT_YMAX[self.rfe_mode])
        if 'device_settings.iq_output_path' in changed:
            if 'CONNECTOR' in state.device_settings['iq_output_path']:
                # remove plots
                self._plot_group.hide()
                self.trace_group.hide()
                self._plot_layout.hide()
                if self._main_window.isMaximized():
                    self._main_window.showNormal()

                # resize window
                for x in range(self.plot_width):
                    self._grid.setColumnMinimumWidth(x, 0)
                screen = QtGui.QDesktopWidget().screenGeometry()

                self.setMinimumWidth(0)
                self.setMinimumHeight(0)
                self._main_window.setMinimumWidth(0)
                self._main_window.setMinimumHeight(0)
                self.resize(0,0)
                self._main_window.resize(0,0)

            elif 'DIGITIZER' in state.device_settings['iq_output_path']:
                # show plots
                self._plot_group.show()
                self.trace_group.show()
                self._plot_layout.show()

                # resize window
                for x in range(self.plot_width):
                    self._grid.setColumnMinimumWidth(x, 300)
                screen = QtGui.QDesktopWidget().screenGeometry()
                self.setMinimumWidth(screen.width() * 0.7)
                self.setMinimumHeight(screen.height() * 0.6)

    def keyPressEvent(self, event):
        if self.dut_prop:
            hotkey_util(self, event)

    def mousePressEvent(self, event):
            if self.controller._dut:
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
        self.plot_width = 8

        for x in range(self.plot_width):
            grid.setColumnMinimumWidth(x, 300)

        grid.addWidget(self._plot_layout(),0,0,13,self.plot_width)

        self.marker_labels = []
        marker_label, delta_label, diff_label = self._marker_labels()
        self.marker_labels.append(marker_label)
        self.marker_labels.append(delta_label)
        grid.addWidget(marker_label, 0, 1, 1, 2)
        grid.addWidget(delta_label, 0, 3, 1, 2)
        grid.addWidget(diff_label , 0, 5, 1, 2)

        y = 0
        x = self.plot_width

        controls_layout = QtGui.QVBoxLayout()
        controls_layout.addWidget(self._trace_controls())

        controls_layout.addWidget(self._plot_controls())
        controls_layout.addWidget(self._device_controls())
        controls_layout.addWidget(self._freq_controls())
        controls_layout.addStretch()
        grid.addLayout(controls_layout, y, x, 13, 5)

        self._grid = grid
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
        self.trace_group = TraceControls()
        self.trace_group.trace_attr['store'].clicked.connect(lambda: cu._store_trace(self))
        self.trace_group.trace_attr['max_hold'].clicked.connect(lambda: cu.max_hold(self))
        self.trace_group.trace_attr['min_hold'].clicked.connect(lambda: cu.min_hold(self))
        self.trace_group.trace_attr['write'].clicked.connect(lambda: cu.trace_write(self))
        self.trace_group.trace_attr['blank'].clicked.connect(lambda: cu.blank_trace(self))
        self.trace_group.trace_tab.currentChanged.connect(lambda: cu._trace_tab_change(self))
        self.control_widgets.append(self.trace_group)
        return self.trace_group

    def _dsp_controls(self):
        self._dsp_group = DSPWidget()
        self.control_widgets.append(self._dsp_group)
        return self._dsp_group

    def _device_controls(self):
        self._dev_group = DeviceControls(self.controller)
        self.control_widgets.append(self._dev_group)
        return self._dev_group

    def _freq_controls(self):
        self._freq_group = FrequencyControls(self.controller)
        self.control_widgets.append(self._freq_group)
        return self._freq_group

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
        third_row.addWidget(self._peak_left())
        third_row.addWidget(self._peak_control())
        third_row.addWidget(self._peak_right())

        fourth_row = QtGui.QHBoxLayout()
        ref_level, ref_label, min_level, min_label = self._ref_controls()

        fourth_row.addWidget(ref_label)
        fourth_row.addWidget(ref_level)
        fourth_row.addWidget(min_label)
        fourth_row.addWidget(min_level)

        fifth_row = QtGui.QHBoxLayout()
        fifth_row.addWidget(self._cf_marker())
        fifth_row.addWidget(self._center_control())

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

    def _peak_right(self):
        peak = QtGui.QPushButton('Peak Right')
        peak.setToolTip("Find peak right of current peak")
        peak.clicked.connect(lambda: cu._find_right_peak(self))
        self._peak = peak
        self.control_widgets.append(self._peak)
        return peak

    def _peak_left(self):
        peak = QtGui.QPushButton('Peak Left')
        peak.setToolTip("Find peak left of current peak")
        peak.clicked.connect(lambda: cu._find_left_peak(self))
        self._peak = peak
        self.control_widgets.append(self._peak)
        return peak

    def _center_control(self):
        center = QtGui.QPushButton('Recenter')
        center.setToolTip("[C]\nCenter the Plot View around the available spectrum") 
        center.clicked.connect(lambda: self._plot.center_view(min(self.xdata), 
                                                            max(self.xdata),
                                                            min_level = int(self._min_level.text()),
                                                            ref_level = int(self._ref_level.text())))
        self._center_bt = center
        self.control_widgets.append(self._center_bt)
        return center

    def _cf_marker(self):
        cf_marker = QtGui.QPushButton('Marker to Center Frequency')
        cf_marker.setToolTip("Center the frequency on the current marker") 

        def cf_marker_click():
            current_marker = self._marker_tab.currentIndex()
            marker = self._plot.markers[current_marker]

            if marker.enabled:
                self._freq_group.change_center_freq(self.xdata[marker.data_index])
                marker.data_index = len(self.pow_data)/2
        cf_marker.clicked.connect(cf_marker_click)

        self.cf_marker = cf_marker
        self.control_widgets.append(self.cf_marker)
        return cf_marker
    def _ref_controls(self):
        ref_level = QtGui.QLineEdit(str(PLOT_YMAX))
        ref_level.returnPressed.connect(lambda: self._plot.center_view(min(self.xdata), 
                                                                        max(self.xdata),
                                                                        min_level = int(self._min_level.text()),
                                                                        ref_level = int(self._ref_level.text())))
        self._ref_level = ref_level
        self.control_widgets.append(self._ref_level)
        ref_label = QtGui.QLabel('Maximum Level: ')
        
        min_level = QtGui.QLineEdit(str(PLOT_YMIN)) 
        min_level.returnPressed.connect(lambda: self._plot.center_view(min(self.xdata), 
                                                                        max(self.xdata),
                                                                        min_level = int(self._min_level.text()),
                                                                        ref_level = int(self._ref_level.text())))
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

    def capture_received(self, state, fstart, fstop, raw, power, usable, segments):
        """
        :param state: SpecAState when capture was requested
        :param fstart: lowest frequency included in data in Hz
        :param fstop: highest frequency included in data in Hz
        :param raw: raw samples (None if not available)
        :param power: power spectrum
        :param usable: usable bins from power (None when sweeping)
        :param segments: bin segments from power (None when not sweeping)
        """
        self.raw_data = raw
        self.pow_data = power
        self.usable_bins = usable
        self.sweep_segments = segments

        self.xdata = np.linspace(fstart, fstop, len(power))

        self.update_trace()
        if self.freq_range != (fstart, fstop):
            self.freq_range = (fstart, fstop)
            self._plot.center_view(fstart, fstop)
        self.update_iq()
        self.update_marker()
        self.update_diff()

    def update_trace(self):

        #FIXME make alternate_colors user defined
        for trace in self._plot.traces:
            trace.update_curve(
                self.xdata,
                self.pow_data,
                self.usable_bins,
                self.sweep_segments,
                self.plot_state.alt_colors)

    def update_iq(self):

        if not self.raw_data:
                return
        trace = self._plot.traces[self.trace_group.trace_tab.currentIndex()]

        if not (trace.write or trace.max_hold or trace.min_hold or trace.store):
            return
        if not trace.store:
            data_pkt = self.raw_data
            trace.raw_packet = self.raw_data
        else:
            data_pkt = trace.raw_packet

        if data_pkt.stream_id == VRT_IFDATA_I14Q14:
            data = data_pkt.data.numpy_array()
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
            data = data_pkt.data.numpy_array()
            i_data = np.array(data, dtype=float)

            if data_pkt.stream_id == VRT_IFDATA_I14:
                i_data = i_data /ZIF_BITS

            elif data_pkt.stream_id == VRT_IFDATA_I24:
                i_data = i_data / (np.mean(i_data)) - 1
            self._plot.i_curve.setData(i_data)

            self._plot.q_curve.clear()

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
            
            delta_text = 'Delta : %0.1f MHz \nDelta %0.2f dB' % (freq_diff, power_diff )
            self._diff_lab.setText(delta_text)
        else:
            self._diff_lab.setText('')

    def enable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(True)

        for key in self.trace_group.trace_attr:
            self.trace_group.trace_attr[key].setEnabled(True)
        
    def disable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(False)

        for key in self.trace_group.trace_attr:
            self.trace_group.trace_attr[key].setEnabled(False)

        
