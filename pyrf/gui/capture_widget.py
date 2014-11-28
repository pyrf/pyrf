from PySide import QtGui, QtCore
from pyrf.gui.util import hide_layout
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.widgets import QCheckBoxPlayback, QComboBoxPlayback, QDoubleSpinBoxPlayback
from pyrf.units import M

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

        self._mode = QComboBoxPlayback()
        self._mode.setToolTip("Change the device input mode")

        self._level_trigger = QCheckBoxPlayback("Level Trigger")
        self._level_trigger.setToolTip("Enable Frequency Level Triggers")

        self._trig_fstart_label = QtGui.QLabel("Start:")
        self._trig_fstart = QDoubleSpinBoxPlayback()

        # FIXME: use values from device properties
        self._trig_fstart.setRange(0, 20000)
        self._trig_fstart.setSuffix(" MHz")

        self._trig_fstop_label = QtGui.QLabel("Stop:")
        self._trig_fstop = QDoubleSpinBoxPlayback()
        # FIXME: use values from device properties
        self._trig_fstop.setRange(0, 20000)
        self._trig_fstop.setSuffix(" MHz")

        self._trig_amp_label = QtGui.QLabel("Level:")
        self._trig_amp = QDoubleSpinBoxPlayback()
        self._trig_amp.setSuffix(" dBm")
        self._trig_amp.setRange(-2000, 2000)

    def _build_layout(self, dut_prop=None):

        grid = self.layout()

        grid.addWidget(self._mode_label, 0, 0, 1, 1)
        grid.addWidget(self._mode, 0, 1, 1, 2)

        grid.addWidget(self._conts_box, 0, 3, 1, 1)
        grid.addWidget(self._single_button, 0, 4, 1, 1)
        grid.addWidget(self._level_trigger, 1, 0, 1, 2)

        grid.addWidget(self._trig_fstart_label, 2, 0, 1, 1)
        grid.addWidget(self._trig_fstart, 2, 1, 1, 1)

        grid.addWidget(self._trig_fstop_label, 2, 3, 1, 1)
        grid.addWidget(self._trig_fstop, 2, 4, 1, 1)

        grid.addWidget(self._trig_amp_label, 1, 3, 1, 1)
        grid.addWidget(self._trig_amp, 1, 4, 1, 1)
        self._trig_state(False)

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

        def enable_trigger():
            trigger_settings = self.gui_state.device_settings['trigger']
            if self._level_trigger.isChecked():
                self._trig_state(True)

                start = self.gui_state.center - (self.gui_state.span / 4)
                stop = self.gui_state.center + (self.gui_state.span / 4)
                level = trigger_settings['amplitude']
                self.controller.apply_device_settings(trigger = {'type': 'LEVEL',
                                                                'fstart': start,
                                                                'fstop': stop,
                                                                'amplitude': trigger_settings['amplitude']})
            else:
                self.controller.apply_device_settings(trigger = {'type': 'NONE',
                                                                'fstart': trigger_settings['fstart'],
                                                                'fstop': trigger_settings['fstop'],
                                                                'amplitude': trigger_settings['amplitude']})
                self._trig_state(False)

        def new_trigger():
            self.controller.apply_device_settings(trigger = {'type': 'LEVEL',
                                                    'fstart': self._trig_fstart.value() * M,
                                                    'fstop': self._trig_fstop.value() * M,
                                                    'amplitude': self._trig_amp.value()})

        self._mode.currentIndexChanged.connect(new_input_mode)
        self._single_button.clicked.connect(single_capture)
        self._conts_box.clicked.connect(cont_capture)
        self._level_trigger.clicked.connect(enable_trigger)
        self._trig_fstart.editingFinished.connect(new_trigger)
        self._trig_fstop.editingFinished.connect(new_trigger)
        self._trig_amp.editingFinished.connect(new_trigger)

    def device_changed(self, dut):
        self.dut_prop = dut.properties
        self._update_modes()

    def state_changed(self, state, changed):
        self.gui_state = state
        if 'playback' in changed:
            # restore controls after playback is stopped
            self._level_trigger.setEnabled(state.mode in self.dut_prop.LEVEL_TRIGGER_RFE_MODES)
            self._update_modes(current_mode=state.mode)
            self._level_trigger.playback_value(False)

        if state.playback:
            # for playback simply update on every state change
            self._mode.playback_value(MODE_TO_TEXT[state.mode])
        
        if 'device_settings.trigger' in changed:
            if state.device_settings['trigger']['type'] == 'LEVEL':
                trigger = state.device_settings['trigger']
                self._trig_fstart.quiet_update(value=trigger['fstart'] / M)
                self._trig_fstop.quiet_update(value=trigger['fstop'] / M)
                self._trig_amp.quiet_update(value=trigger['amplitude'])
            else:
                if self._level_trigger.checkState():
                    self._level_trigger.click()

        if 'device_settings.iq_output_path' in changed:
            if state.device_settings['iq_output_path'] == 'CONNECTOR':
                self._update_modes(include_sweep=False)
                self._level_trigger.setEnabled(False)
                self._trig_fstart.setEnabled(False)
                self._trig_fstop.setEnabled(False)
                self._trig_amp.setEnabled(False)

            elif state.device_settings['iq_output_path'] == 'DIGITIZER':
                self._update_modes()
                self._trig_fstart.setEnabled(True)
                self._trig_fstop.setEnabled(True)
                self._trig_amp.setEnabled(True)
                self._level_trigger.setEnabled(True)

        if 'mode' in changed:
            if state.mode not in self.dut_prop.LEVEL_TRIGGER_RFE_MODES:
                # forcibly disable triggers
                if self._level_trigger.isChecked():
                    self._level_trigger.click()
                self._trig_state(False)
                self._level_trigger.setEnabled(False)

            else:
                self._level_trigger.setEnabled(True)

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

    def _trig_state(self, state):
        self._trig_fstart.setEnabled(state)
        self._trig_amp.setEnabled(state)
        self._trig_fstop.setEnabled(state)
        self._trig = state

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)



