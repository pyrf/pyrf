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
import time
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
from pyrf.gui.capture_widget import CaptureControls
from pyrf.gui.marker_controls import MarkerControls, MarkerTable

VIEW_OPTIONS = [
    ('&IQ Plots', 'iq_plots', False),
    ('&Spectrogram', 'waterfall_plot', False),
    ('&Persistence Plot', 'persistence_plot', False),
    ]

DEVELOPER_OPTIONS = [
    ('Show &Attenuated Edges', 'show_attenuated_edges', False),
    ('Show &Sweep Steps', 'show_sweep_steps', False),
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

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.update_title)
        self.update_timer.start(100)

    def initUI(self, dut_address, playback_filename):
        self.mainPanel = MainPanel(self.controller, self)
        self._device_address = dut_address
        self._device_id = None
        self.update_title()
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
        save_config_action = QtGui.QAction('&Save Settings', self)
        save_config_action.triggered.connect(self.save_configuration)
        load_config_action = QtGui.QAction('&Load Settings', self)
        load_config_action.triggered.connect(self.load_configuration)
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
        file_menu.addAction(load_config_action)
        file_menu.addAction(save_config_action)
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
        self.option_actions = {}
        for text, option, default in VIEW_OPTIONS:
            self.option_actions[option] = checkbox_action(self.controller.apply_options, text, option, default)
            self.view_menu.addAction(self.option_actions[option])

        self.view_menu.addSeparator()

        if developer_menu:
            self.developer_menu = menubar.addMenu('D&eveloper Options')
            for text, option, default in DEVELOPER_OPTIONS:
                self.developer_menu.addAction(checkbox_action(
                    self.controller.apply_options, text, option, default))

        self.controller.apply_options(
            **dict((option, default) for text, option, default
            in VIEW_OPTIONS + DEVELOPER_OPTIONS))

    def start_recording(self):

        filename = time.strftime('recording-%Y-%m-%d-%H%M%S')
        names = glob.glob(filename + '*.vrt')
        if (filename + '.vrt') in names:
            count = names.count(filename)
            filename += '(%d)' % count
        filename += '.vrt'
        record_filename, file_type = QtGui.QFileDialog.getSaveFileName(self,
            "Create Recording",
            filename,
            "VRT Packet Capture Files (*.vrt)",
            )
        if record_filename:
            self.stop_action.setDisabled(False)
            self.record_action.setDisabled(True)
            self.controller.start_recording(record_filename)

    def stop_recording(self):
        self.stop_action.setDisabled(True)
        self.record_action.setDisabled(False)
        self.controller.stop_recording()

    def open_device_dialog(self):
        self.discovery_widget = DiscoveryWidget(
            open_device_callback=self.open_device,
            name="Open Device")
        self.discovery_widget.show()

    def open_playback_dialog(self):
        playback_filename, file_type = QtGui.QFileDialog.getOpenFileName(self,
            "Play Recording", None, "VRT Packet Capture Files (*.vrt)")
        if playback_filename:
            self.controller.set_device(None)
            self.start_playback(playback_filename)

    def start_csv(self):
        filename = time.strftime('csv-%Y-%m-%d-%H%M%S')
        names = glob.glob(filename + '*.csv')

        if (filename + '.csv') in names:
            count = names.count(filename)
            filename += '(%d)' % count
        filename += '.csv'
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
        self.update_title()
        self.controller.set_device(playback_filename=playback_filename)
        self.show()

    def save_configuration(self):
        filename = time.strftime('config-%Y-%m-%d-%H%M%S')
        names = glob.glob(filename + '*.config')

        if (filename + '.config') in names:
            count = names.count(filename)
            filename += '(%d)' % count
        filename += '.config'
        cfilename, file_type = QtGui.QFileDialog.getSaveFileName(self,
                                                                "PyRF Configuration File", 
                                                                filename, 
                                                                "PyRF Configuration File (*.config)")
        if cfilename == '':
            return
        self.controller.save_settings(cfilename)

    def load_configuration(self):
        cfilename, file_type = QtGui.QFileDialog.getOpenFileName(self,
                                                                "PyRF Configuration File", 
                                                                None, 
                                                                "PyRF Configuration File (*.config)")
        if cfilename == '':
            return
        self.controller.load_settings(cfilename)

    def update_title(self):
        if self._device_id is None:
            manufacutrer = ''
        else:
            manufacutrer = (self._device_id.split(',') + ['', '', ''])[0]

        current_time = time.strftime('%Y/%m/%d %I:%M:%S %p')
        spaces = ''
        for x in range(int(self.size().width() / 15)):
            spaces += ' '
        self.setWindowTitle((manufacutrer + '  %s' % current_time)+ spaces + 'PyRF RTSA %s Connected To: %s' % (__version__ , self._device_address))

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
        self.dut_prop = dut.properties
        
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
        controller.window_change.connect(self.window_changed)
        self._main_window = main_window

        self.ref_level = 0
        self.dut = None
        self.control_widgets = {}
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
        self._waterfall_range = None, None, None

        self.options_changed(controller.get_options(),
            ['iq_plots', 'waterfall_plot', 'persistence_plot'])
        self.start_time = time.time()

    def device_changed(self, dut):
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
            if rfe_mode in ('DD', 'IQIN'):
                freq = self.dut_prop.MIN_TUNABLE[rfe_mode]
                full_bw = self.dut_prop.FULL_BW[rfe_mode]

                self._plot.center_view(freq,
                                       full_bw)
                self._plot.center_iq_plots()
            else:
                freq = state.center
                full_bw = state.span

                self._plot.center_view(freq - full_bw/2,
                                        freq + full_bw/2)
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
                self.mask_label.setVisible(False) 
            else:
                # show plots
                self._plot_layout.show()
                # resize window
                for x in range(self.plot_width):
                    self._grid.setColumnMinimumWidth(x, 300)
                screen = QtGui.QDesktopWidget().screenGeometry()
                self.setMinimumWidth(MINIMUM_WIDTH)
                self.setMinimumHeight(MINIMUM_HEIGHT)
                WINDOW_WIDTH = max(screen.width() * 0.7, MINIMUM_WIDTH)
                WINDOW_HEIGHT = max(screen.height() * 0.7, MINIMUM_HEIGHT)
                self._main_window.resize(WINDOW_WIDTH,WINDOW_HEIGHT)
                self.mask_label.setVisible(True) 

    def plot_changed(self, state, changed):
        self.plot_state = state

    def window_changed(self, state, changed):
        """
        signal handler for window changes
        :param state: new windowState object
        :param changed: list of attribute names changed
        """
        for win in changed:
            if not self.control_widgets[win].isVisible() and state[win]:
                self.control_widgets[win].show()
            if self.control_widgets[win].isVisible() and not state[win]:
                self.control_widgets[win].close()

    def show_labels(self):
        for c in self.channel_power_labels:
            c.show()

    def hide_labels(self):
        for c in self.channel_power_labels:
            c.hide()

    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        self.plot_width = 13

        for x in range(self.plot_width):
            grid.setColumnMinimumWidth(x, 300)

        self.mask_label = QtGui.QLabel()
        self.mask_label.setStyleSheet('background-color: rgb(0,0,0)')
        grid.addWidget(self.mask_label, 0, 0, 15, self.plot_width)
        marker_table = MarkerTable(self.controller)
        channel_power_labels = self._channel_power_labels()
        grid.addWidget(marker_table, 0, 0, 1, self.plot_width)

        grid.addWidget(self._plot_layout(), 1, 0, 14, self.plot_width)
        x = 1
        for label in channel_power_labels:
            grid.addWidget(label, 1, x, 1, 2)
            x += 3
        self._init_docking_widgets()

        self._grid = grid
        self.setLayout(grid)

    def _init_docking_widgets(self):
        self._toggle_actions = {}
        self._add_docking_controls(self._freq_controls(), "Frequency Control")
        self._add_docking_controls(
            self._measurement_controls(), "Measurement Control")
        self._add_docking_controls(self._marker_controls(), "Marker Control")
        self._add_docking_controls(
            self._capture_controls(), "Capture Control")
        self._add_docking_controls(
            self._amplitude_controls(), "Amplitude Control")
        self._add_docking_controls(self._device_controls(), "Device Control")
        self._add_docking_controls(self._trace_controls(), "Trace Control")

    def _add_docking_controls(self, widget, title):

        def title_to_key(title):
        # function to convert title to dict key
            return title.lower().replace(' ', '_')

        dock = QtGui.QDockWidget(title, self)
        dock.setAllowedAreas(
            QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea | QtCore.Qt.BottomDockWidgetArea)
        dock.setWidget(widget)

        self._main_window.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
        toggle_action = dock.toggleViewAction()
        def _dock_change():
            window_name = {title_to_key(title): toggle_action.isChecked()}
            self.controller.apply_window_options(**window_name)

        toggle_action.toggled.connect(_dock_change)
        self._toggle_actions[title_to_key(title)] = toggle_action
        self._main_window.view_menu.addAction(toggle_action)
        self.control_widgets[title_to_key(title)] = dock

    def _plot_layout(self):
        vsplit = QtGui.QSplitter()
        vsplit.setOrientation(QtCore.Qt.Vertical)
        vsplit.addWidget(self._plot.spectral_window)

        if self._plot.waterfall_window:
            vsplit.addWidget(self._plot.waterfall_window)

        persist = QtGui.QHBoxLayout()
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
        return self._freq_group

    def _amplitude_controls(self):
        self._amplitude_group = AmplitudeControls(self.controller, self._plot)
        return self._amplitude_group

    def _trace_controls(self):
        self._trace_group = TraceControls(self.controller)
        return self._trace_group

    def _measurement_controls(self):
        self._measure_group = MeasurementControls(self.controller)
        return self._measure_group

    def _capture_controls(self):
        self._capture_group = CaptureControls(self.controller)
        return self._capture_group

    def _device_controls(self):
        self._dev_group = DeviceControls(self.controller)

        return self._dev_group
        
    def _marker_controls(self):
        self.marker_group = MarkerControls(self.controller, self._plot)
        return self.marker_group

    def _marker_labels(self):
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)

        span_label = QtGui.QLabel('')
        span_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        span_label.setAlignment(QtCore.Qt.AlignLeft)
        span_label.setSizePolicy(sizePolicy)

        rbw_label = QtGui.QLabel('')
        rbw_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        rbw_label.setAlignment(QtCore.Qt.AlignRight)
        rbw_label.setSizePolicy(sizePolicy)

        self._rbw_label = rbw_label
        self._span_label = span_label

        return  rbw_label, span_label

    def _channel_power_labels(self):
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)
        self.channel_power_labels = []

        for color in colors.TRACE_COLORS:
            label = QtGui.QLabel('')
            label.setSizePolicy(sizePolicy)
            label.setAlignment(QtCore.Qt.AlignLeft)
            label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + color))
            label.setMinimumWidth(200)
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

        self.xdata = np.linspace(fstart, fstop, len(power))
        self.update_channel_power()

        if (not self.controller.applying_user_xrange() and self.plot_state['mouse_tune']):
            self._plot.center_view(fstart,
                                   fstop)

        if self.iq_plots_enabled:
            self.update_iq()

        if self.waterfall_plot_enabled or self.persistence_plot_enabled:
            if (fstart, fstop, len(power)) != self._waterfall_range:
                self._plot.waterfall_data.reset(self.xdata)
                self._waterfall_range = (fstart, fstop, len(power))
            self._plot.waterfall_data.add_row(power)

        self.start_time = time.time()

    def options_changed(self, options, changed):
        self.iq_plots_enabled = options['iq_plots']
        self.waterfall_plot_enabled = options['waterfall_plot']
        self.persistence_plot_enabled = options['persistence_plot']

        if 'iq_plots' in changed:
            self._update_iq_plot_visibility()
            self._main_window.option_actions['iq_plots'].setChecked(options['iq_plots'])

        ww = self._plot.waterfall_window
        if 'waterfall_plot' in changed and ww:
            self._main_window.option_actions['waterfall_plot'].setChecked(options['waterfall_plot'])
            if self.waterfall_plot_enabled:
                ww.show()
            else:
                ww.hide()

        if 'persistence_plot' in changed:
            self._main_window.option_actions['persistence_plot'].setChecked(options['persistence_plot'])
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

    def update_iq(self):
        if not self.raw_data:
                return
        self._plot.update_iq_plots(self.raw_data)

    def update_channel_power(self):
        for label, trace in zip(self.channel_power_labels, self._plot.traces):
            if trace.calc_channel_power and not trace.blank:
                label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + trace.color))
                label.setText(("Channel Power: %0.2f dBm" % trace.channel_power))
            else:
                label.setText('')

    def enable_controls(self):

        for item in self.control_widgets:
            self.control_widgets[item].setEnabled(True)

    def disable_controls(self):
        for item in self.control_widgets:
            self.control_widgets[item].setEnabled(False)

