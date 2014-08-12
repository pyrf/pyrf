from PySide import QtGui, QtCore
from pyrf.units import M
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.util import clear_layout
from pyrf.gui.widgets import (QComboBoxPlayback, QCheckBoxPlayback,
    QDoubleSpinBoxPlayback)

# FIXME: calculate choices from device properties instead
RBW_VALUES = [976.562, 488.281, 244.141, 122.070, 61.035, 30.518, 15.259, 7.62939, 3.815]
HDR_RBW_VALUES = [1271.56, 635.78, 317.890, 158.94, 79.475, 39.736, 19.868, 9.934]

class DeviceControls(QtGui.QGroupBox):
    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to control the WSA4000/WSA5000
    :param name: The name of the groupBox
    """

    def __init__(self, controller, name="Device Control"):
        super(DeviceControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)
        self.setStyleSheet(GROUP_BOX_FONT)
        self.setTitle(name)

        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()
        self._connect_device_controls()

    def _create_controls(self):
        self._mode_label = QtGui.QLabel('Mode:')
        self._mode = QComboBoxPlayback()
        self._mode.setToolTip("Change the device input mode")

        self._rbw_label = QtGui.QLabel('RBW:')
        self._rbw_box = QComboBoxPlayback()
        self._rbw_box.setToolTip("Change the RBW of the FFT plot")
        self._update_rbw_options()

        self._dec_label = QtGui.QLabel('DDC:')
        self._dec_box = QComboBoxPlayback()
        self._dec_box.setToolTip("Choose Decimation Rate")
        # FIXME: use values from device properties
        dec_values = ['1', '4', '8', '16', '32', '64', '128', '256', '512', '1024']
        for d in dec_values:
            self._dec_box.addItem(d)
        self._dec_values = dec_values

        self._fshift_label = QtGui.QLabel("FShift:")
        self._fshift_edit = QDoubleSpinBoxPlayback()
        self._fshift_edit.setSuffix(' MHz')
        self._fshift_edit.setToolTip("Frequency Shift")
        self._fshift_edit.setWrapping(True)

        self._antenna_label = QtGui.QLabel('Antenna:')
        self._antenna_box = QComboBoxPlayback()
        self._antenna_box.setToolTip("Choose Antenna")
        self._antenna_box.quiet_update(["Antenna 1", "Antenna 2"])

        self._iq_output_label = QtGui.QLabel("IQ Path:")
        self._iq_output_box = QComboBoxPlayback()
        self._iq_output_box.setToolTip("Choose IQ Path")
        self._iq_output_box.quiet_update(["Digitizer", "Connector"])

        self._gain_label = QtGui.QLabel("RF Gain:")
        self._gain_box = QComboBoxPlayback()
        self._gain_box.setToolTip("Choose RF Gain setting")
        gain_values = ['VLow', 'Low', 'Med', 'High']
        self._gain_box.quiet_update(gain_values)
        self._gain_values = [g.lower() for g in gain_values]

        self._ifgain_label = QtGui.QLabel("IF Gain:")
        self._ifgain_box = QtGui.QSpinBox()
        self._ifgain_box.setToolTip("Choose IF Gain setting")
        # FIXME: use values from device properties
        self._ifgain_box.setRange(-10, 25)
        self._ifgain_box.setSuffix(" dB")

        self._pll_label = QtGui.QLabel("PLL Ref:")
        self._pll_box = QComboBoxPlayback()
        self._pll_box.setToolTip("Choose PLL Reference")
        self._pll_box.quiet_update(["Internal", "External"])

        self._level_trigger = QCheckBoxPlayback("Level Trigger")
        self._level_trigger.setToolTip("Enable Frequency Level Triggers")

        self._trig_fstart_label = QtGui.QLabel("Start:")
        self._trig_fstart = QDoubleSpinBoxPlayback()
        # FIXME: use values from device properties
        self._trig_fstart.setRange(0, 20000)
        self._trig_fstart.setSuffix(" MHz")
        self._trig_fstart.lineEdit().setReadOnly(True)

        self._trig_fstop_label = QtGui.QLabel("Stop:")
        self._trig_fstop = QDoubleSpinBoxPlayback()
        # FIXME: use values from device properties
        self._trig_fstop.setRange(0, 20000)
        self._trig_fstop.setSuffix(" MHz")
        self._trig_fstop.lineEdit().setReadOnly(True)

        self._trig_amp_label = QtGui.QLabel("Level:")
        self._trig_amp = QDoubleSpinBoxPlayback()
        self._trig_amp.setSuffix(" dBm")
        self._trig_amp.setRange(-2000, 2000)
        self._trig_amp.lineEdit().setReadOnly(True)

    def _build_layout(self, dut_prop=None):
        features = dut_prop.SWEEP_SETTINGS if dut_prop else []

        grid = self.layout()
        clear_layout(grid)

        grid.addWidget(self._mode_label, 0, 0, 1, 1)
        grid.addWidget(self._mode, 0, 1, 1, 1)
        grid.addWidget(self._rbw_label, 0, 3, 1, 1)
        grid.addWidget(self._rbw_box, 0, 4, 1, 1)

        grid.addWidget(self._dec_label, 1, 0, 1, 1)
        grid.addWidget(self._dec_box, 1, 1, 1, 1)
        grid.addWidget(self._fshift_label, 1, 3, 1, 1)
        grid.addWidget(self._fshift_edit, 1, 4, 1, 1)

        # 4k features
        if 'antenna' in features:
            grid.addWidget(self._antenna_label, 2, 3, 1, 1)
            grid.addWidget(self._antenna_box, 2, 4, 1, 1)

        if 'gain' in features:
            grid.addWidget(self._gain_label, 3, 0, 1, 1)
            grid.addWidget(self._gain_box, 3, 1, 1, 1)

            # FIXME: 'ifgain' appears in 5k list too
            grid.addWidget(self._ifgain_label, 3, 3, 1, 1)
            grid.addWidget(self._ifgain_box, 3, 4, 1, 1)

        # 5k features
        if 'attenuator' in features:

            # FIXME: 'iq_output' isn't in device properties yet
            grid.addWidget(self._iq_output_label, 3, 3, 1, 1)
            grid.addWidget(self._iq_output_box, 3, 4, 1, 1)
            
            grid.addWidget(self._pll_label, 3, 0, 1, 1)
            grid.addWidget(self._pll_box, 3, 1, 1, 1)

        grid.addWidget(self._level_trigger, 4, 0, 1, 2)

        grid.addWidget(self._trig_fstart_label, 5, 0, 1, 1)
        grid.addWidget(self._trig_fstart, 5, 1, 1, 1)

        grid.addWidget(self._trig_fstop_label, 5, 3, 1, 1)
        grid.addWidget(self._trig_fstop, 5, 4, 1, 1)
        
        grid.addWidget(self._trig_amp_label, 6, 0, 1, 1)
        grid.addWidget(self._trig_amp, 6, 1, 1, 1)
        self._trig_state(False)

        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 4)
        grid.setColumnStretch(4, 8)

    def _connect_device_controls(self):
        def new_antenna():
            self.controller.apply_device_settings(antenna=
                int(self._antenna_box.currentText().split()[-1]))

        def new_dec():
            self.controller.apply_settings(decimation=int(
                self._dec_box.currentText()))

        def new_freq_shift():
            self.controller.apply_settings(
                fshift=self._fshift_edit.value() * M)

        def new_gain():
            self.plot_state.dev_set['gain'] = self._gain_box.currentText().split()[-1].lower().encode('ascii')
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_ifgain():
            self.plot_state.dev_set['ifgain'] = self._ifgain_box.value()
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_pll_reference():
            if self._pll_box.currentText() == 'Internal':
                src = 'INT'
            else:
                src = 'EXT'
            self.controller.apply_device_settings(pll_reference=src)

        def new_iq_path():
            self.controller.apply_device_settings(
                iq_output_path= str(self._iq_output_box.currentText().upper()))

        def new_input_mode():
            input_mode = self._mode.currentText()
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
        def new_rbw():
            self.controller.apply_settings(rbw=self._rbw_values[
                self._rbw_box.currentIndex()])

        self._antenna_box.currentIndexChanged.connect(new_antenna)
        self._gain_box.currentIndexChanged.connect(new_gain)
        self._dec_box.currentIndexChanged.connect(new_dec)
        self._fshift_edit.valueChanged.connect(new_freq_shift)
        self._ifgain_box.valueChanged.connect(new_ifgain)
        self._mode.currentIndexChanged.connect(new_input_mode)
        self._iq_output_box.currentIndexChanged.connect(new_iq_path)
        self._pll_box.currentIndexChanged.connect(new_pll_reference)
        self._level_trigger.clicked.connect(enable_trigger)
        self._trig_fstart.valueChanged.connect(new_trigger)
        self._trig_fstop.valueChanged.connect(new_trigger)
        self._trig_amp.valueChanged.connect(new_trigger)
        self._rbw_box.currentIndexChanged.connect(new_rbw)

    def device_changed(self, dut):
        self.dut_prop = dut.properties
        self._build_layout(self.dut_prop)
        self._update_modes()


    def _update_modes(self, include_sweep=True):
        modes = []
        if include_sweep:
            modes.extend(self.dut_prop.SPECA_MODES)
        modes.extend(self.dut_prop.RFE_MODES)
        self._mode.quiet_update(modes)


    def state_changed(self, state, changed):
        self.gui_state = state

        if state.playback:
            # for playback simply update everything on every state change
            self._mode.playback_value(state.mode)
            self._level_trigger.playback_value(False)
            self._dec_box.playback_value(str(state.decimation))
            self._fshift_edit.playback_value(state.fshift / M)
            self._rbw_box.playback_value(str(state.rbw))
            self._pll_box.playback_value('External'
                if state.device_settings.get('pll_reference') == 'EXT' else
                'Internal')
            self._iq_output_box.playback_value('Digitizer')
            return

        if 'playback' in changed:
            # restore controls after playback is stopped
            self._update_modes()
            self._level_trigger.setEnabled(
                state.mode in self.dut_prop.LEVEL_TRIGGER_RFE_MODES)
            decimation_available = self.dut_prop.MIN_DECIMATION[
                state.rfe_mode()] is not None
            self._dec_box.setEnabled(decimation_available)
            self._fshift_edit.setEnabled(decimation_available)
            self._update_rbw_options()
            self._pll_box.quiet_update(["Internal", "External"])
            self._pll_box.setEnabled(True)
            self._iq_output_box.quiet_update(["Digitizer", "Connector"])
            self._iq_output_box.setEnabled(True)

        if 'center' in changed:
            if self._level_trigger.isChecked():
                self._level_trigger.click()
        if 'mode' in changed:
            if state.mode not in self.dut_prop.LEVEL_TRIGGER_RFE_MODES:
                self._level_trigger.setEnabled(False)

                # forcibly disable triggers
                if self._level_trigger.isChecked():
                    self._level_trigger.click()
                    self.rig_state(False)

            else:
                self._level_trigger.setEnabled(True)

            if state.sweeping():
                self._dec_box.setEnabled(False)
                self._fshift_edit.setEnabled(False)
            else:
                decimation_available = self.dut_prop.MIN_DECIMATION[
                    state.rfe_mode()] is not None
                self._dec_box.setEnabled(decimation_available)
                self._fshift_edit.setEnabled(decimation_available)
            fshift_max = self.dut_prop.FULL_BW[state.rfe_mode()] / M
            self._fshift_edit.setRange(-fshift_max, fshift_max)

            self._update_rbw_options()

        if 'device_settings.iq_output_path' in changed:
            if 'CONNECTOR' in state.device_settings['iq_output_path']:
                # remove sweep capture modes
                self._update_modes()
                c = self._mode.count()

                # remove all sweep modes while using IQ out
                self._update_modes(include_sweep=False)

                if state.sweeping():
                    self._mode.setCurrentIndex(0)

                # remove all digitizer controls
                self._rbw_label.hide()
                self._rbw_box.hide()
                self._dec_box.hide()
                self._fshift_edit.hide()
                self._fshift_label.hide()

            elif 'DIGITIZER' in state.device_settings['iq_output_path']:
                # show digitizer controls
                self._rbw_label.show()
                self._rbw_box.show()
                self._dec_box.show()
                self._fshift_edit.show()
                self._fshift_label.show()
                # insert all sweep modes only if no sweep mode is in the combo box
                self._update_modes()

        if 'device_settings.trigger' in changed:
            if state.device_settings['trigger']['type'] == 'LEVEL':
                trigger = state.device_settings['trigger']
                self._trig_fstart.quiet_update(value=trigger['fstart'] / M)
                self._trig_fstop.quiet_update(value=trigger['fstop'] / M)
                self._trig_amp.quiet_update(value=trigger['amplitude'])

    def _rbw_replace_items(self, items):
        for i in range(self._rbw_box.count()):
            self._rbw_box.removeItem(0)
        self._rbw_box.addItems(items)

    def _update_rbw_options(self):
        """
        populate RBW drop-down with reasonable values for the current mode
        """
        # FIXME: calculate values from FULL_BW[rfe_mode] instead
        if hasattr(self, 'gui_state') and self.gui_state.rfe_mode() == 'HDR':
            self._rbw_use_hdr_values()
        else:
            self._rbw_use_normal_values()

    def _rbw_use_normal_values(self):
        values = [v * 1000 for v in RBW_VALUES]  # wat
        self._rbw_values = values
        self._rbw_box.quiet_update(
            [str(p) + ' KHz' for p in RBW_VALUES])

    def _rbw_use_hdr_values(self):
        values = HDR_RBW_VALUES
        self._rbw_values = values
        self._rbw_box.quiet_update(
            [str(p) + ' Hz' for p in HDR_RBW_VALUES])

    def _trig_state(self, state):
        self._trig_fstart.setEnabled(state)
        self._trig_amp.setEnabled(state)
        self._trig_fstop.setEnabled(state)
        self._trig = state
