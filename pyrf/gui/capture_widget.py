from PySide import QtGui, QtCore
from pyrf.gui.util import hide_layout
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.widgets import QCheckBoxPlayback, QComboBoxPlayback

# FIXME: move to device properties?
MODE_TO_TEXT = {
    'Sweep SH': 'Sweep',
    'Sweep ZIF': 'Sweep (100 MHz steps)',
    'ZIF': '100 MHz span',
    'SH': '40 MHz span',
    'SHN': '10 MHz span',
    'HDR': '0.1 MHz span',
    'DD': 'Baseband',
    'IQIN': 'IQIN',
}
TEXT_TO_MODE = dict((m,t) for (t,m) in MODE_TO_TEXT.iteritems())

class CaptureControls(QtGui.QWidget):
    """
    A widget with a layout containing widgets that
    can be used to control the amplitude configurations of the GUI
    :param name: A controller that emits/receives Qt signals from multiple widgets
    :param name: The name of the groupBox
    """

    def __init__(self, controller):
        super(CaptureControls, self).__init__()

        self.controller = controller
        controller.plot_change.connect(self.plot_changed)
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        grid = QtGui.QGridLayout()
        self.setLayout(QtGui.QGridLayout())

        self._create_controls()
        self._build_layout()
        self._connect_capture_controls()

    def _create_controls(self):
        self._conts_box = QCheckBoxPlayback("Continuous")
        self._conts_box.setChecked(True)

        self._single_button = QtGui.QPushButton('Single')

        self._mode_label = QtGui.QLabel('Mode:')
        # self._mode_label.setMaximumWidth(40)
        self._mode = QComboBoxPlayback()
        self._mode.setToolTip("Change the device input mode")

    def _build_layout(self, dut_prop=None):

        grid = self.layout()

        grid.addWidget(self._mode_label, 0, 0, 1, 1)
        grid.addWidget(self._mode, 0, 1, 1, 2)

        grid.addWidget(self._conts_box, 0, 3, 1, 1)
        grid.addWidget(self._single_button, 0, 4, 1, 1)

        self.setLayout(grid)
        self.resize_widget()

    def _connect_capture_controls(self):

        def single_capture():
            self.controller.apply_plot_options(cont_cap_mode = False)
            self.controller.start_capture(single = True)

        def cont_capture():
            self.controller.apply_plot_options(cont_cap_mode = self._conts_box.isChecked())
            if self._conts_box.isChecked():
                self.controller.start_capture(single = True)

        def new_input_mode():
            input_mode = TEXT_TO_MODE[self._mode.currentText()]
            if not input_mode:
                return
            self.controller.apply_settings(mode=input_mode)
            #FIXME rfe_mode should not be in device settings dictionary
            if self.gui_state.device_settings['iq_output_path'] == 'CONNECTOR':
                self.controller.apply_device_settings(rfe_mode = input_mode)

        self._mode.currentIndexChanged.connect(new_input_mode)
        self._single_button.clicked.connect(single_capture)
        self._conts_box.clicked.connect(cont_capture)

    def device_changed(self, dut):
        self.dut_prop = dut.properties
        self._update_modes()

    def state_changed(self, state, changed):
        self.gui_state = state
        if 'playback' in changed:
            self._update_modes(current_mode=state.mode)
        if state.playback:
            # for playback simply update on every state change
            self._mode.playback_value(MODE_TO_TEXT[state.mode])
        
        if 'device_settings.iq_output_path' in changed:
            if state.device_settings['iq_output_path'] == 'CONNECTOR':
                self._update_modes(include_sweep=False)
            elif state.device_settings['iq_output_path'] == 'DIGITIZER':
                self._update_modes()

    def plot_changed(self, state, changed):
        if 'cont_cap_mode' in changed:
            if not state['cont_cap_mode']:
                if self._conts_box.isChecked():
                    self._conts_box.click()

    def _update_modes(self, include_sweep=True, current_mode=None):
        modes = []
        if current_mode:
            current_mode = MODE_TO_TEXT[current_mode]
        if include_sweep:

            modes.extend(self.dut_prop.SPECA_MODES)
            if not self.controller.developer_mode:
                modes.remove('Sweep ZIF')
        modes.extend(self.dut_prop.RFE_MODES)

        self._mode.quiet_update((MODE_TO_TEXT[m] for m in modes), current_mode)
        self._mode.setEnabled(True)

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)



