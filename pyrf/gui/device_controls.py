from PySide import QtGui
from pyrf.units import M

from pyrf.gui.util import clear_layout
from pyrf.gui.widgets import QComboBoxPlus

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

        self.setTitle(name)

        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()
        self._connect_device_controls()

    def _create_controls(self):
        self._mode_label = QtGui.QLabel('Mode:')
        self._mode = QComboBoxPlus()
        self._mode.setToolTip("Change the device input mode")

        self._rbw_label = QtGui.QLabel('RBW:')
        self._rbw_box = QtGui.QComboBox()
        self._rbw_box.setToolTip("Change the RBW of the FFT plot")
        self._rbw_values = None
        self._rbw_use_normal_values()

        self._dec_label = QtGui.QLabel('Decimation:')
        self._dec_box = QtGui.QComboBox()
        self._dec_box.setToolTip("Choose Decimation Rate")
        # FIXME: use values from device properties
        dec_values = ['1', '4', '8', '16', '32', '64', '128', '256', '512', '1024']
        for d in dec_values:
            self._dec_box.addItem(d)
        self._dec_values = dec_values

        self._fshift_label = QtGui.QLabel("FShift:")
        self._fshift_edit = QtGui.QDoubleSpinBox()
        self._fshift_edit.setSuffix(' MHz')
        self._fshift_edit.setToolTip("Frequency Shift")

        self._antenna_label = QtGui.QLabel('Antenna:')
        self._antenna_box = QtGui.QComboBox()
        self._antenna_box.setToolTip("Choose Antenna")
        self._antenna_box.addItem("Antenna 1")
        self._antenna_box.addItem("Antenna 2")

        self._iq_output_label = QtGui.QLabel("IQ Path:")
        self._iq_output_box = QtGui.QComboBox()
        self._iq_output_box.setToolTip("Choose IQ Path")
        self._iq_output_box.addItem("Digitizer")
        self._iq_output_box.addItem("Connector")

        self._gain_label = QtGui.QLabel("RF Gain:")
        self._gain_box = QtGui.QComboBox()
        self._gain_box.setToolTip("Choose RF Gain setting")
        gain_values = ['VLow', 'Low', 'Med', 'High']
        for g in gain_values:
            self._gain_box.addItem(g)
        self._gain_values = [g.lower() for g in gain_values]

        self._ifgain_label = QtGui.QLabel("IF Gain:")
        self._ifgain_box = QtGui.QSpinBox()
        self._ifgain_box.setToolTip("Choose IF Gain setting")
        self._ifgain_box.setRange(-10, 25)
        self._ifgain_box.setSuffix(" dB")

        self._attenuator_box = QtGui.QCheckBox("Attenuator")
        self._attenuator_box.setChecked(True)

        self._pll_label = QtGui.QLabel("PLL Ref:")
        self._pll_box = QtGui.QComboBox()
        self._pll_box.setToolTip("Choose PLL Reference")
        self._pll_box.addItem("Internal")
        self._pll_box.addItem("External")

        self._level_trigger = QtGui.QCheckBox("Level Trigger")
        self._level_trigger.setToolTip("Enable Frequency Level Triggers")

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

        grid.addWidget(self._level_trigger, 2, 0, 1, 2)

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
            grid.addWidget(self._attenuator_box, 2, 3, 1, 2)

            # FIXME: 'pll_reference' isn't in device properties yet
            grid.addWidget(self._pll_label, 3, 0, 1, 1)
            grid.addWidget(self._pll_box, 3, 1, 1, 1)

            # FIXME: 'iq_output' isn't in device properties yet
            grid.addWidget(self._iq_output_label, 3, 3, 1, 1)
            grid.addWidget(self._iq_output_box, 3, 4, 1, 1)

        grid.setColumnStretch(0, 5)
        grid.setColumnStretch(1, 7)
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

        def new_attenuator():
            self.controller.apply_device_settings(attenuator = self._attenuator_box.isChecked())

        def new_pll_reference():
            if self._pll_box.currentText() == 'Internal':
                src = 'INT'
            else:
                src = 'EXT'
            self.controller.apply_device_settings(pll_reference=src)

        def new_iq_path():
            self.controller.apply_device_settings(
                iq_output_path=self._iq_output_box.currentText().upper())

        def new_input_mode():
            input_mode = self._mode.currentText()
            if not input_mode:
                return

            self.controller.enable_user_xrange_control(input_mode == 'Auto')
            if input_mode == 'Auto':
                input_mode = self.dut_prop.SPECA_MODES[0]

            self.controller.apply_settings(mode=input_mode)

        def new_trigger():
            trigger_settings = self.gui_state.device_settings['trigger']
            if self._level_trigger.isChecked():
                start = self.gui_state.center - (self.gui_state.span / 2) + 20e6
                stop = self.gui_state.center + (self.gui_state.span / 2) - 20e6
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

        def new_rbw():
            self.controller.apply_settings(rbw=self._rbw_values[
                self._rbw_box.currentIndex()])

        self._antenna_box.currentIndexChanged.connect(new_antenna)
        self._gain_box.currentIndexChanged.connect(new_gain)
        self._dec_box.currentIndexChanged.connect(new_dec)
        self._fshift_edit.valueChanged.connect(new_freq_shift)
        self._ifgain_box.valueChanged.connect(new_ifgain)
        self._attenuator_box.clicked.connect(new_attenuator)
        self._mode.currentIndexChanged.connect(new_input_mode)
        self._iq_output_box.currentIndexChanged.connect(new_iq_path)
        self._pll_box.currentIndexChanged.connect(new_pll_reference)
        self._level_trigger.clicked.connect(new_trigger)
        self._rbw_box.currentIndexChanged.connect(new_rbw)

    def device_changed(self, dut):
        self.dut_prop = dut.properties
        self._build_layout(self.dut_prop)
        self._update_modes()


    def _update_modes(self):
        modes = ["Auto"]
        modes.extend(self.dut_prop.SPECA_MODES)
        modes.extend(self.dut_prop.RFE_MODES)
        self._mode.update_items_no_signal(modes)


    def state_changed(self, state, changed):
        self.gui_state = state

        if 'playback' in changed:
            if state.playback:
                self._mode.playback_value(state.mode)
                self._level_trigger.setEnabled(False)
                self._dec_box.setEnabled(False)
                self._fshift_edit.setEnabled(False)
            else:
                self._update_modes()
                self._level_trigger.setEnabled(
                    state.mode in self.dut_prop.LEVEL_TRIGGER_RFE_MODES)
                decimation_available = self.dut_prop.MIN_DECIMATION[
                    state.rfe_mode()] is not None
                self._dec_box.setEnabled(decimation_available)
                self._fshift_edit.setEnabled(decimation_available)

        if 'center' in changed:
            if self._level_trigger.isChecked():
                self._level_trigger.click()
        if 'mode' in changed:
            if state.mode not in self.dut_prop.LEVEL_TRIGGER_RFE_MODES:
                self._level_trigger.setEnabled(False)
                if self._level_trigger.isChecked():
                    self._level_trigger.click()
            else:
                self._level_trigger.setEnabled(True)

            if state.sweeping():
                self._dec_box.setEnabled(False)
                self._fshift_edit.setEnabled(False)
            decimation_available = self.dut_prop.MIN_DECIMATION[
                state.rfe_mode()] is not None
            self._dec_box.setEnabled(decimation_available)
            self._fshift_edit.setEnabled(decimation_available)
            fshift_max = self.dut_prop.FULL_BW[state.mode] / M
            self._fshift_edit.setMaximum(fshift_max)
            self._fshift_edit.setMinimum(-fshift_max)

            # FIXME: calculate values from FULL_BW[rfe_mode] instead
            if state.rfe_mode() == 'HDR':
                self._rbw_use_hdr_values()
            else:
                self._rbw_use_normal_values()

            # FIXME: way too much knowledge about rbw levels here
            self._rbw_box.setCurrentIndex(
                0 if state.sweeping() else
                4 if state.mode in ['SH', 'SHN'] else 3)

        if 'device_settings.iq_output_path' in changed:
            if 'CONNECTOR' in state.device_settings['iq_output_path']:
                # remove sweep capture modes
                c = self._mode.count()
                self._mode.removeItem(0)
                self._mode.setCurrentIndex(0)
                # remove all digitizer controls
                self._dec_box.hide()
                self._fshift_edit.hide()
                self._fshift_label.hide()

            elif 'DIGITIZER' in state.device_settings['iq_output_path']:
                # add sweep SH mode
                if not self._mode.itemText(0) == 'Auto':
                    self._mode.insertItem(0, 'Auto')

                # show digitizer controls
                self._dec_box.show()
                self._fshift_edit.show()
                self._fshift_label.show()

    def _rbw_replace_items(self, items):
        for i in range(self._rbw_box.count()):
            self._rbw_box.removeItem(0)
        self._rbw_box.addItems(items)

    def _rbw_use_normal_values(self):
        values = [v * 1000 for v in RBW_VALUES]  # wat
        if values == self._rbw_values:
            return
        self._rbw_values = values
        self._rbw_replace_items([str(p) + ' KHz' for p in RBW_VALUES])

    def _rbw_use_hdr_values(self):
        values = HDR_RBW_VALUES
        if values == self._rbw_values:
            return
        self._rbw_values = values
        self._rbw_replace_items([str(p) + ' Hz' for p in HDR_RBW_VALUES])

        def new_rbw():
            self.controller.apply_settings(rbw=self._rbw_values[
                rbw.currentIndex()])

        rbw.setCurrentIndex(0)
        rbw.currentIndexChanged.connect(new_rbw)
        return rbw_label, rbw


