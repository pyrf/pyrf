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
import glob

from pkg_resources import parse_version, require

from pyrf.gui import colors
from pyrf.gui import fonts
from pyrf.gui import labels
from pyrf.gui import gui_config
from pyrf.gui.controller import SpecAController
from pyrf.version import __version__
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.config import TriggerSettings, TRIGGER_TYPE_LEVEL
from pyrf.units import M
from pyrf.devices.thinkrf import WSA

from pyrf.gui.util import find_nearest_index
from pyrf.gui.plot_widget import Plot
from pyrf.gui.device_controls import DeviceControls
from pyrf.gui.frequency_controls import FrequencyControls
from pyrf.gui.amplitude_controls import AmplitudeControls
from pyrf.gui.discovery_widget import DiscoveryWidget
from pyrf.gui.trace_controls import TraceControls
from pyrf.gui.measurements_widget import MeasurementControls

VIEW_OPTIONS = [
    ('&IQ Plots', 'iq_plots', False),
    ('&Spectrogram', 'waterfall_plot', False),
    ('&Persistence Plot', 'persistence_plot', False),
    ]

DEVELOPER_OPTIONS = [
    ('Show &Attenuated Edges', 'show_attenuated_edges', False),
    ('Show &Sweep Steps', 'show_sweep_steps', False),
    ('&Free Plot Adjustment', 'free_plot_adjustment', False),
    ('&IQ Offset Correction', 'dsp.correct_phase', True),
    ('&DC Offset', 'dsp.hide_differential_dc_offset', True),
    ('Apply &Spectral Inversion', 'dsp.apply_spec_inv', True),
    ('Apply &Hanning Window', 'dsp.apply_window', True),
    ]

MINIMUM_WIDTH = 600
MINIMUM_HEIGHT = 600

try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass


class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, dut_address=None, playback_filename=None,
            developer_menu=False):
        super(MainWindow, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        WINDOW_WIDTH = max(screen.width() * 0.7, MINIMUM_WIDTH)
        WINDOW_HEIGHT = max(screen.height() * 0.6, MINIMUM_HEIGHT)
        self.resize(WINDOW_WIDTH,WINDOW_HEIGHT)

        self.controller = SpecAController(developer_menu)
        self.controller.device_change.connect(self.device_changed)
        self.init_menu_bar(developer_menu)
        self.initUI(dut_address, playback_filename)

    def initUI(self, dut_address, playback_filename):
        self.mainPanel = MainPanel(self.controller, self)

        self.setWindowTitle('PyRF RTSA: ' + __version__)
        self.setCentralWidget(self.mainPanel)
        if dut_address:
            self.open_device(dut_address, True)
        elif playback_filename:
            self.start_playback(playback_filename)
        else:
            self.open_device_dialog()

    def init_menu_bar(self, developer_menu=False):

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
        self.start_csv_export = QtGui.QAction('&Start Exporting CSV', self)
        self.start_csv_export.triggered.connect(self.start_csv)
        self.stop_csv_export = QtGui.QAction('&Stop Exporting CSV', self)
        self.stop_csv_export.triggered.connect(self.stop_csv)
        self.stop_csv_export.setDisabled(True)
        self.device_info = QtGui.QAction('Device &Information', self)
        self.device_info.triggered.connect(self.get_device_information)
        self.device_info.setDisabled(True)
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
        file_menu.addAction(self.start_csv_export)
        file_menu.addAction(self.stop_csv_export)
        file_menu.addSeparator()
        file_menu.addAction(self.device_info)
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

        self.view_menu = menubar.addMenu('&View')
        for text, option, default in VIEW_OPTIONS:
            self.view_menu.addAction(checkbox_action(
                self.controller.apply_options, text, option, default))

        if developer_menu:
            self.developer_menu = menubar.addMenu('D&eveloper Options')
            for text, option, default in DEVELOPER_OPTIONS:
                self.developer_menu.addAction(checkbox_action(
                    self.controller.apply_options, text, option, default))

        self.controller.apply_options(
            **dict((option, default) for text, option, default
            in VIEW_OPTIONS + DEVELOPER_OPTIONS))

    def start_recording(self):
        self.stop_action.setDisabled(False)
        names = glob.glob('recording-*.vrt')
        last_index = -1
        for n in names:
            try:
                last_index = max(last_index, int(n[10:-4]))
            except ValueError:
                pass
        filename = 'recording-%04d.vrt' % (last_index + 1)
        record_filename, file_type = QtGui.QFileDialog.getSaveFileName(self,
            "Create Recording",
            filename,
            "VRT Packet Capture Files (*.vrt)",
            )
        if record_filename:
            self.controller.start_recording(record_filename)

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

    def start_csv(self):

        names = glob.glob('csv-*.csv')
        last_index = -1
        for n in names:
            try:
                last_index = max(last_index, int(n[4:-4]))

            except ValueError:
                pass
        filename = 'csv-%04d.csv' % (last_index + 1)
        playback_filename, file_type = QtGui.QFileDialog.getSaveFileName(self,
            "CSV File", filename, "CSV File (*.csv)")

        if playback_filename:
            self.controller.start_csv_export(playback_filename)
            self.start_csv_export.setDisabled(True)
            self.stop_csv_export.setDisabled(False)

    def stop_csv(self):
        self.start_csv_export.setDisabled(False)
        self.stop_csv_export.setDisabled(True)
        self.controller.stop_csv_export()

    def start_playback(self, playback_filename):
        self.record_action.setDisabled(True)
        self.stop_action.setDisabled(True)
        self.device_info.setDisabled(False)
        self._device_address = playback_filename
        self.controller.set_device(playback_filename=playback_filename)
        self.show()

    def device_changed(self, dut):
        if not dut:
            self._device_address = None
            self._device_id = None
        self._device_id = dut.device_id

    def get_device_information(self):
        info = QtGui.QMessageBox()
        device_parts = self._device_id.split(',') + ['', '', '']
        hardware, serial, firmware = device_parts[1:4]
        info.setText('''
Connected to: %s

Serial number: %s
Hardware version: %s
Firmware version: %s'''.strip() % (
                self._device_address,
                serial,
                hardware,
                firmware,
                ))
        info.exec_()

    @inlineCallbacks
    def open_device(self, name, ok):
        if not ok:
            self.show()
            return

        self.show()
        dut = WSA(connector=TwistedConnector(self._get_reactor()))
        yield dut.connect(name)
        self._device_address = name
        self.setWindowTitle('PyRF RTSA %s Connected To: %s' % (__version__ , name))
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
        self.device_info.setDisabled(False)

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
        controller.plot_change.connect(self.plot_changed)
        controller.capture_receive.connect(self.capture_received)
        controller.options_change.connect(self.options_changed)

        self._main_window = main_window

        self.ref_level = 0
        self.dut = None
        self.control_widgets = []
        super(MainPanel, self).__init__()
        screen = QtGui.QDesktopWidget().screenGeometry()
        self.setMinimumWidth(MINIMUM_WIDTH)
        self.setMinimumHeight(MINIMUM_HEIGHT)
        self.plot_state = None
        self.gui_state = None
        # plot window
        self._plot = Plot(controller, self)
        self._plot.user_xrange_change.connect(controller.user_xrange_changed)

        self._vrt_context = {}
        self.initUI()
        self.disable_controls()
        self.plot_state = None

        self._waterfall_range = None, None, None

        self.options_changed(controller.get_options(),
            ['iq_plots', 'waterfall_plot', 'persistence_plot'])

    def device_changed(self, dut):
        self.plot_state = gui_config.PlotState(dut.properties)
        self.trace_group.plot_state = self.plot_state
        self.dut_prop = dut.properties

        self.enable_controls()

    def state_changed(self, state, changed):
        """
        signal handler for speca state changes
        :param state: new SpecAState object
        :param changed: list of attribute names changed
        """
        self.gui_state = state
        if 'mode' in changed:
            rfe_mode = state.rfe_mode()
            self._update_iq_plot_visibility()
            self.update_rbw_label()
            if rfe_mode in ('DD', 'IQIN'):
                freq = self.dut_prop.MIN_TUNABLE[rfe_mode]
                full_bw = self.dut_prop.FULL_BW[rfe_mode]

                self._plot.center_view(freq,
                                       full_bw,
                                       self._amplitude_group.get_min_level(),
                                       self._amplitude_group.get_max_level())
                self._plot.center_iq_plots()
            else:
                freq = state.center
                full_bw = state.span

                self._plot.center_view(freq - full_bw/2,
                                        freq + full_bw/2,
                                       self._amplitude_group.get_min_level(),
                                       self._amplitude_group.get_max_level())
                self._plot.center_iq_plots()
        if 'device_settings.iq_output_path' in changed:
            if state.device_settings['iq_output_path'] == 'CONNECTOR':
                # remove plots
                self._plot_layout.hide()
                self.hide_labels()
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
            else:
                # show plots
                self._plot_layout.show()
                self.show_labels()
                # resize window
                for x in range(self.plot_width):
                    self._grid.setColumnMinimumWidth(x, 300)
                screen = QtGui.QDesktopWidget().screenGeometry()
                self.setMinimumWidth(MINIMUM_WIDTH)
                self.setMinimumHeight(MINIMUM_HEIGHT)
                WINDOW_WIDTH = max(screen.width() * 0.7, MINIMUM_WIDTH)
                WINDOW_HEIGHT = max(screen.height() * 0.7, MINIMUM_HEIGHT)
                self._main_window.resize(WINDOW_WIDTH,WINDOW_HEIGHT)

        if 'rbw' in changed:
            self.update_rbw_label()

        if 'span' in changed:
            self.update_span_label()

    def plot_changed(self, state, changed):
        self.plot_state = state

    def show_labels(self):
        self._rbw_label.show()
        self._span_label.show()
        self._diff_label.show()
        self._mask_label.show()
        for m in self.marker_labels:
            m.show()
        for c in self.channel_power_labels:
            c.show()

    def hide_labels(self):
        self._rbw_label.hide()
        self._span_label.hide()
        self._diff_label.hide()
        self._mask_label.hide()
        for m in self.marker_labels:
            m.hide()
        for c in self.channel_power_labels:
            c.hide()

    def update_rbw_label(self):
        rfe_mode = self.gui_state.rfe_mode()
        if rfe_mode == 'HDR':
            self._rbw_label.setText("RBW:\n%0.2f Hz" % (self.gui_state.rbw))
        else:
            self._rbw_label.setText("RBW:\n%0.2f KHz" % (self.gui_state.rbw / 1e3))

    def update_span_label(self):
        rfe_mode = self.gui_state.rfe_mode()
        if rfe_mode == 'HDR':
            self._span_label.setText("SPAN:\n%0.2f KHz" % (self.gui_state.span / 1e3))
        else:
            self._span_label.setText("SPAN:\n%0.2f MHz" % (self.gui_state.span/ M))

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        self.plot_width = 11

        for x in range(self.plot_width):
            grid.setColumnMinimumWidth(x, 300)

        self._mask_label = QtGui.QLabel()
        self._mask_label.setStyleSheet('background-color: black')

        self.marker_labels = []
        marker_label, delta_label, diff_label, rbw_label, span_label = self._marker_labels()
        channel_power_labels = self._channel_power_labels()
        grid.addWidget(self._mask_label, 0, 0, 2, self.plot_width)
        grid.addWidget(marker_label, 0, 3, 1, 2)
        grid.addWidget(delta_label, 0, 5, 1, 2)
        grid.addWidget(diff_label , 0, 7, 1, 2)
        grid.addWidget(self._rbw_label, 0, 0, 1, 2)
        grid.addWidget(self._span_label, 0, 9, 1, 2)
        grid.addWidget(self._plot_layout(), 1, 0, 14, self.plot_width)
        x = 2
        for label in channel_power_labels:
            grid.addWidget(label, 1, x, 1, 2)
            x += 3
        y = 0
        x = self.plot_width
        controls_layout = QtGui.QVBoxLayout()

        controls_layout.addWidget(self._freq_controls())
        controls_layout.addWidget(self._measurement_controls())
        controls_layout.addWidget(self._amplitude_controls())
        controls_layout.addWidget(self._device_controls())
        controls_layout.addWidget(self._trace_controls())
        controls_layout.addStretch()
        grid.addLayout(controls_layout, y, x, 14, 5)

        self._grid = grid
        self.setLayout(grid)

    def _plot_layout(self):
        vsplit = QtGui.QSplitter()
        vsplit.setOrientation(QtCore.Qt.Vertical)
        vsplit.addWidget(self._plot.window)
        if self._plot.waterfall_window:
            vsplit.addWidget(self._plot.waterfall_window)
        
        persist = QtGui.QHBoxLayout()
        # FIXME: reaching too far into plot..
        persist.addWidget(self._plot.persistence_window.gradient_editor)
        persist.addWidget(self._plot.persistence_window)
        persist_widget = QtGui.QWidget()
        persist_widget.setLayout(persist)
        self.persist_widget = persist_widget
        vsplit.addWidget(persist_widget)

        hsplit = QtGui.QSplitter()
        hsplit.addWidget(self._plot.const_window)
        hsplit.addWidget(self._plot.iq_window)
        self._plot.const_window.hide()
        self._plot.iq_window.hide()
        vsplit.addWidget(hsplit)

        self._plot_layout = vsplit
        return self._plot_layout

    def _freq_controls(self):
        self._freq_group = FrequencyControls(self.controller)
        self.control_widgets.append(self._freq_group)
        return self._freq_group

    def _amplitude_controls(self):
        self._amplitude_group = AmplitudeControls(self.controller, self._plot)
        self.control_widgets.append(self._amplitude_group)
        return self._amplitude_group

    def _trace_controls(self):
        self.trace_group = TraceControls(self.controller, self._plot)
        self.control_widgets.append(self.trace_group)
        return self.trace_group

    def _measurement_controls(self):
        self.measure_group = MeasurementControls(self.controller)
        self.control_widgets.append(self.measure_group)
        return self.measure_group

    def _dsp_controls(self):
        self._dsp_group = DSPWidget()
        self.control_widgets.append(self._dsp_group)
        return self._dsp_group

    def _device_controls(self):
        self._dev_group = DeviceControls(self.controller)
        self.control_widgets.append(self._dev_group)
        return self._dev_group

    def _marker_labels(self):
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)

        marker_label = QtGui.QLabel('')
        marker_label.setAlignment(QtCore.Qt.AlignLeft)
        marker_label.setSizePolicy(sizePolicy)

        delta_label = QtGui.QLabel('')
        delta_label.setAlignment(QtCore.Qt.AlignLeft)
        delta_label.setSizePolicy(sizePolicy)

        span_label = QtGui.QLabel('')
        span_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        span_label.setAlignment(QtCore.Qt.AlignLeft)
        span_label.setSizePolicy(sizePolicy)

        rbw_label = QtGui.QLabel('')
        rbw_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        rbw_label.setAlignment(QtCore.Qt.AlignRight)
        rbw_label.setSizePolicy(sizePolicy)

        diff_label = QtGui.QLabel('')
        diff_label.setAlignment(QtCore.Qt.AlignLeft)
        diff_label.setSizePolicy(sizePolicy)
        self._diff_label = diff_label
        self._rbw_label = rbw_label
        self._span_label = span_label
        self.marker_labels.append(marker_label)

        self.marker_labels.append(delta_label)
        return marker_label,delta_label, diff_label, rbw_label, span_label

    def _channel_power_labels(self):
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)

        self.channel_power_labels = []

        for color in colors.TRACE_COLORS:
            label = QtGui.QLabel('')
            label.setSizePolicy(sizePolicy)
            label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + color))
            self.channel_power_labels.append(label)
        return self.channel_power_labels

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
        self.update_marker()
        self.update_diff()
        self.update_channel_power()
        if (not self.controller.applying_user_xrange() and
                not self.controller.get_options()['free_plot_adjustment']):
            self._plot.center_view(fstart,
                                   fstop,
                                   self._amplitude_group.get_min_level(),
                                   self._amplitude_group.get_max_level())

        if self.iq_plots_enabled:
            self.update_iq()

        if self.waterfall_plot_enabled or self.persistence_plot_enabled:
            if (fstart, fstop, len(power)) != self._waterfall_range:
                self._plot.waterfall_data.reset(self.xdata)
                self._waterfall_range = (fstart, fstop, len(power))
            self._plot.waterfall_data.add_row(power)


    def options_changed(self, options, changed):
        self.iq_plots_enabled = options['iq_plots']
        self.waterfall_plot_enabled = options['waterfall_plot']
        self.persistence_plot_enabled = options['persistence_plot']

        if 'iq_plots' in changed:
            self._update_iq_plot_visibility()

        ww = self._plot.waterfall_window
        if 'waterfall_plot' in changed and ww:
            if self.waterfall_plot_enabled:
                ww.show()
            else:
                ww.hide()

        if 'persistence_plot' in changed:
            self.persist_widget.setVisible(self.persistence_plot_enabled)

    def _update_iq_plot_visibility(self):
        if not self.gui_state:
            return
        if self.gui_state.sweeping() or not self.iq_plots_enabled:
            self._plot.const_window.hide()
            self._plot.iq_window.hide()
        else:
            self._plot.const_window.show()
            self._plot.iq_window.show()

        ww = self._plot.waterfall_window
        if ww:
            if self.waterfall_plot_enabled:
                ww.show()
            else:
                ww.hide()

    def update_trace(self):
        for trace in self._plot.traces:
            trace.update_curve(
                self.xdata,
                self.pow_data,
                self.usable_bins,
                self.sweep_segments)

    def update_iq(self):

        if not self.raw_data:
                return
        self._plot.update_iq_plots(self.raw_data)

    def update_marker(self):
            num = 1
            for marker, marker_label in zip(self._plot.markers, self.marker_labels):
                if marker.enabled:
                    trace = self._plot.traces[marker.trace_index]
                    marker_label.show()
                    if not trace.blank:

                        marker_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + marker.draw_color))
                        marker.update_pos(trace.freq_range, trace.data)
                        if self.gui_state.rfe_mode() == 'HDR':
                            marker_text = 'M%d: %0.4f MHz \n %0.2f dBm' % (num, trace.freq_range[marker.data_index]/1e6, 
                                                                           trace.data[marker.data_index])
                        else:
                            marker_text = 'M%d: %0.2f MHz \n %0.2f dBm' % (num, trace.freq_range[marker.data_index]/1e6, 
                                                                                   trace.data[marker.data_index])
                        num += 1
                        marker_label.setText(marker_text)
                        self._mask_label.show()
                else:
                    marker_label.hide()

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

            self._diff_label.show()

            freq_diff = np.abs((traces[0].freq_range[data_indices[0]]/1e6) - (traces[1].freq_range[data_indices[1]]/1e6))

            power_diff = np.abs((traces[0].data[data_indices[0]]) - (traces[1].data[data_indices[1]]))
            self._diff_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
            if self.gui_state.rfe_mode() == 'HDR':
                delta_text = 'Delta: %0.2f KHz \n %0.2f dB' % (freq_diff * 1000, power_diff )
            else:
                delta_text = 'Delta: %0.1f MHz \n %0.2f dB' % (freq_diff, power_diff )
            self._diff_label.setText(delta_text)
        else:
            self._diff_label.hide()

    def update_channel_power(self):

        for label, trace in zip(self.channel_power_labels, self._plot.traces):
            if trace.calc_channel_power and not trace.blank:
                label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + trace.color))
                label.setText(("Channel Power: %0.2f dBm" % trace.channel_power))
            else:
                label.setText('')

    def enable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(True)

    def disable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(False)

