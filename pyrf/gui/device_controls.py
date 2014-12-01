from PySide import QtGui, QtCore
from pyrf.units import M
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.util import clear_layout
from pyrf.gui.widgets import (QComboBoxPlayback, QCheckBoxPlayback,
    QDoubleSpinBoxPlayback)

class DeviceControls(QtGui.QWidget):
    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to control the WSA4000/WSA5000
    :param name: The name of the groupBox
    """

    def __init__(self, controller):
        super(DeviceControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()
        self._connect_device_controls()

    def _create_controls(self):
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

    def _build_layout(self, dut_prop=None):
        features = dut_prop.SWEEP_SETTINGS if dut_prop else []

        grid = self.layout()
        clear_layout(grid)

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
            if dut_prop.IQ_OUTPUT_CONNECTOR:
                grid.addWidget(self._iq_output_label, 3, 3, 1, 1)
                grid.addWidget(self._iq_output_box, 3, 4, 1, 1)
            
            grid.addWidget(self._pll_label, 3, 0, 1, 1)
            grid.addWidget(self._pll_box, 3, 1, 1, 1)

        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 8)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 4)
        grid.setColumnStretch(4, 8)
        grid.setRowStretch(7, 1) # expand empty space at the bottom
        self.resize_widget()

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

        self._antenna_box.currentIndexChanged.connect(new_antenna)
        self._gain_box.currentIndexChanged.connect(new_gain)
        self._dec_box.currentIndexChanged.connect(new_dec)
        self._fshift_edit.valueChanged.connect(new_freq_shift)
        self._ifgain_box.valueChanged.connect(new_ifgain)
        self._iq_output_box.currentIndexChanged.connect(new_iq_path)
        self._pll_box.currentIndexChanged.connect(new_pll_reference)

    def device_changed(self, dut):
        self.dut_prop = dut.properties
        self._build_layout(self.dut_prop)

    def state_changed(self, state, changed):

        if state.playback:
            # for playback simply update everything on every state change
            self._dec_box.playback_value(str(state.decimation))
            self._fshift_edit.playback_value(state.fshift / M)
            self._pll_box.playback_value('External'
                if state.device_settings.get('pll_reference') == 'EXT' else
                'Internal')
            self._iq_output_box.playback_value('Digitizer')
            return

        if 'playback' in changed:
            decimation_available = self.dut_prop.MIN_DECIMATION[
                state.rfe_mode()] is not None
            self._dec_box.setEnabled(decimation_available)
            self._fshift_edit.setEnabled(decimation_available)
            self._pll_box.quiet_update(["Internal", "External"])
            self._pll_box.setEnabled(True)
            self._iq_output_box.quiet_update(["Digitizer", "Connector"])
            self._iq_output_box.setEnabled(True)

        if 'device_settings.trigger' in changed:
            if state.device_settings['trigger']['type'] == 'None':
                if self._level_trigger.isChecked():
                    self._level_trigger.click()

        if 'mode' in changed:
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

        if 'device_settings.iq_output_path' in changed:
            if 'CONNECTOR' == state.device_settings['iq_output_path']:
                # remove all digitizer controls
                self._dec_box.setEnabled(False)
                self._fshift_edit.setEnabled(False)
                self._fshift_label.setEnabled(False)
                self._level_trigger.setEnabled(False)
                self._trig_fstart.setEnabled(False)
                self._trig_fstop.setEnabled(False)
                self._trig_amp.setEnabled(False)

            elif 'DIGITIZER' == state.device_settings['iq_output_path']:
                # enable digitizer controls
                if not self.gui_state.device_settings['iq_output_path']  == 'DIGITIZER':
                    self._dec_box.setEnabled(True)
                    self._fshift_edit.setEnabled(True)
                    self._fshift_label.setEnabled(True)
                    self._trig_fstart.setEnabled(True)
                    self._trig_fstop.setEnabled(True)
                    self._trig_amp.setEnabled(True)
                    self._level_trigger.setEnabled(True)

        self.gui_state = state

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)

    def showEvent(self, event):
        self.activateWindow()