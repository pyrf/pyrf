from PySide import QtGui
from pyrf.units import M
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

        dev_layout = QtGui.QVBoxLayout(self)

        row = QtGui.QHBoxLayout()
        row.addWidget(self._mode_control())
        row.addWidget(self._antenna_control())
        row.addWidget(self._iq_output_control())
        dev_layout.addLayout(row)

        row = QtGui.QHBoxLayout()
        row.addWidget(self._attenuator_control())
        row.addWidget(self._pll_reference_control())
        dev_layout.addLayout(row)

        row = QtGui.QHBoxLayout()
        row.addWidget(self._decimation_control())

        fshift_label, fshift_edit, fshift_unit = self._freq_shift_control()
        row.addWidget(fshift_label)
        row.addWidget(fshift_edit)
        row.addWidget(fshift_unit)

        row.addWidget(self._gain_control())
        row.addWidget(self._ifgain_control())
        dev_layout.addLayout(row)

        row = QtGui.QHBoxLayout()
        rbw_label, rbw_box = self._rbw_controls()
        row.addWidget(rbw_label)
        row.addWidget(rbw_box)
        dev_layout.addLayout(row)

        row = QtGui.QHBoxLayout()
        row.addWidget(self._level_trigger_control())
        dev_layout.addLayout(row)

        self.setLayout(dev_layout)
        self.layout = dev_layout

        self._connect_device_controls()

    def _connect_device_controls(self):
        def new_antenna():
            self.controller.apply_device_settings(antenna=
                int(self._antenna_box.currentText().split()[-1]))

        def new_dec():
            self.controller.apply_settings(decimation=int(
                self._dec_box.currentText().split(' ')[-1]))

        def new_freq_shift():
            rfe_mode = 'ZIF'
            prop = self.dut_prop
            max_fshift = prop.MAX_FSHIFT[rfe_mode]
            try:
                if float(self._freq_shift_edit.text()) * M < max_fshift:
                    self.controller.apply_settings(fshift = float(self._freq_shift_edit.text()) * M)
                else:
                    self._freq_shift_edit.setText(str(self.plot_state.dev_set['fshift'] / M))
            except ValueError:
                self._freq_shift_edit.setText(str(self.plot_state.dev_set['fshift'] / M))
                return

        def new_gain():
            self.plot_state.dev_set['gain'] = self._gain_box.currentText().split()[-1].lower().encode('ascii')
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_ifgain():
            self.plot_state.dev_set['ifgain'] = self._ifgain_box.value()
            self.cap_dut.configure_device(self.plot_state.dev_set)

        def new_attenuator():
            self.controller.apply_device_settings(attenuator = self._attenuator_box.isChecked())

        def new_pll_reference():
            if 'INTERNAL' in str(self._pll_box.currentText()):
                src = 'INT'
            else:
                src = 'EXT'
            self.controller.apply_device_settings(pll_reference=src)

        def new_iq_path():
            self.controller.apply_device_settings(iq_output_path = str(self._iq_output_box.currentText().split()[-1]))

        def new_input_mode():
            input_mode = self._mode.currentText()
            if not input_mode:
                return
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


        self._antenna_box.currentIndexChanged.connect(new_antenna)
        self._gain_box.currentIndexChanged.connect(new_gain)
        self._dec_box.currentIndexChanged.connect(new_dec)
        self._freq_shift_edit.returnPressed.connect(new_freq_shift)
        self._ifgain_box.valueChanged.connect(new_ifgain)
        self._attenuator_box.clicked.connect(new_attenuator)
        self._mode.currentIndexChanged.connect(new_input_mode)
        self._iq_output_box.currentIndexChanged.connect(new_iq_path)
        self._pll_box.currentIndexChanged.connect(new_pll_reference)
        self._level_trigger.clicked.connect(new_trigger)

    def device_changed(self, dut):
        self.dut_prop = dut.properties

        # FIXME: remove device-specific code, use device properties instead
        if self.dut_prop.model.startswith('WSA5000'):
            self._antenna_box.hide()
            self._gain_box.hide()
            self._ifgain_box.hide()
            self._iq_output_box.show()
            self._pll_box.show()

        else:
            self._antenna_box.show()
            self._gain_box.show()
            self._attenuator_box.hide()
            self._iq_output_box.hide()
            self._pll_box.hide()

        while self._mode.count():
            self._mode.removeItem(0)
        for m in self.dut_prop.RFE_MODES:
            self._mode.addItem(m)
        if self.dut_prop.model.startswith('WSA5000'):
            self._mode.addItem('Sweep SH')

    def state_changed(self, state, changed):
        self.gui_state = state

        if 'center' in changed:
            if self._level_trigger.isChecked():
                self._level_trigger.click()
        if 'mode' in changed:
            if state.rfe_mode() in ['HDR', 'DD', 'IQIN']:
                self._level_trigger.setEnabled(False)
                if self._level_trigger.isChecked():
                    self._level_trigger.click()
            else:
                self._level_trigger.setEnabled(True)

            if state.sweeping():
                self._dec_box.setEnabled(False)
                self._freq_shift_edit.setEnabled(False)
            elif state.mode == 'HDR':
                self._dec_box.setEnabled(False)
                self._freq_shift_edit.setEnabled(False)
            else:
                self._dec_box.setEnabled(True)
                self._freq_shift_edit.setEnabled(True)

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
                self._mode.removeItem(c - 1)

                # remove all digitizer controls
                self._dec_box.hide()
                self._freq_shift_edit.hide()
                self._fshift_label.hide()
                self._fshift_unit.hide()

            elif 'DIGITIZER' in state.device_settings['iq_output_path']:
                # add sweep SH mode
                self._mode.addItem('Sweep SH')

                # show digitizer controls
                self._dec_box.show()
                self._freq_shift_edit.show()
                self._fshift_label.show()
                self._fshift_unit.show()

    def _antenna_control(self):
        antenna = QtGui.QComboBox(self)
        antenna.setToolTip("Choose Antenna") 
        antenna.addItem("Antenna 1")
        antenna.addItem("Antenna 2")
        self._antenna_box = antenna
        return antenna

    def _iq_output_control(self):
        iq_output = QtGui.QComboBox(self)
        iq_output.setToolTip("Choose IQ Path")
        iq_output.addItem("IQ Path: DIGITIZER")
        iq_output.addItem("IQ Path: CONNECTOR")
        self._iq_output_box = iq_output
        return iq_output

    def _decimation_control(self):
        dec = QtGui.QComboBox(self)
        dec.setToolTip("Choose Decimation Rate") 
        dec_values = ['1', '4', '8', '16', '32', '64', '128', '256', '512', '1024']
        for d in dec_values:
            dec.addItem("Decimation Rate: %s" % d)
        self._dec_values = dec_values
        self._dec_box = dec
        return dec

    def _freq_shift_control(self):
        fshift_label = QtGui.QLabel("Frequency Shift")
        self._fshift_label = fshift_label

        fshift_unit = QtGui.QLabel("MHz")
        self._fshift_unit = fshift_unit

        fshift = QtGui.QLineEdit("0")
        fshift.setToolTip("Frequency Shift") 
        self._freq_shift_edit = fshift

        return fshift_label, fshift, fshift_unit

    def _gain_control(self):
        gain = QtGui.QComboBox(self)
        gain.setToolTip("Choose RF Gain setting") 
        gain_values = ['VLow', 'Low', 'Med', 'High']
        for g in gain_values:
            gain.addItem("RF Gain: %s" % g)
        self._gain_values = [g.lower() for g in gain_values]
        self._gain_box = gain
        return gain

    def _ifgain_control(self):
        ifgain = QtGui.QSpinBox(self)
        ifgain.setToolTip("Choose IF Gain setting")
        ifgain.setRange(-10, 25)
        ifgain.setSuffix(" dB")
        self._ifgain_box = ifgain
        return ifgain

    def _mode_control(self):
        mode = QtGui.QComboBox()
        mode.setToolTip("Change the Input mode of the WSA")
        self._mode = mode
        return mode

    def _attenuator_control(self):
        attenuator = QtGui.QCheckBox("Attenuator")
        attenuator.setChecked(True)
        self._attenuator_box = attenuator
        return attenuator

    def _pll_reference_control(self):
        pll = QtGui.QComboBox(self)
        pll.setToolTip("Choose PLL Reference")
        pll.addItem("PLL Reference: INTERNAL")
        pll.addItem("PLL Reference: EXTERNAL")
        self._pll_box = pll
        return pll

    def _level_trigger_control(self):
        level_trigg = QtGui.QCheckBox("Level Triggers")
        level_trigg.setToolTip("Enable Frequency Level Triggers")
        self._level_trigger = level_trigg
        return level_trigg

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

    def _rbw_controls(self):
        rbw_label = QtGui.QLabel('Resolution Bandwidth:')

        rbw = QtGui.QComboBox(self)
        rbw.setToolTip("Change the RBW of the FFT plot")
        self._rbw_box = rbw
        self._rbw_values = None
        self._rbw_use_normal_values()

        def new_rbw():
            self.controller.apply_settings(rbw=self._rbw_values[
                rbw.currentIndex()])

        rbw.setCurrentIndex(0)
        rbw.currentIndexChanged.connect(new_rbw)
        return rbw_label, rbw


