from PySide import QtGui

class DeviceControlsWidget(QtGui.QGroupBox):

    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to control the WSA4000/WSA5000
    :param name: The name of the groupBox
    
    Note: All the widgets inside this groupBox are not connected to any controls, and must be
    connected within the parent layout.

"""
    def __init__(self, name = "Device Control"):
        super(DeviceControlsWidget, self).__init__()

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

        self.setLayout(dev_layout)
        self.layout = dev_layout

    def configure(self, dut_prop):
        """
        :param dut_prop: device properties object
        """
        if dut_prop.model.startswith('WSA5000'):
            self._antenna_box.hide()
            self._gain_box.hide()
            self._ifgain_box.hide()

        else:
            self._antenna_box.show()
            self._gain_box.show()
            self._attenuator_box.hide()
            self._iq_output_box.hide()
            self._pll_box.hide()

        while self._mode.count():
            self._mode.removeItem(0)
        for m in dut_prop.RFE_MODES:
            self._mode.addItem(m)
        self._mode.addItem('Sweep ZIF')
        self._mode.addItem('Sweep ZIF left band')
        self._mode.addItem('Sweep SH')

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


