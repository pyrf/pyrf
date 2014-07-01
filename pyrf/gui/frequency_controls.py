from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors

SPIN_BOX_HEIGHT = 40


class FrequencyControls(QtGui.QGroupBox):

    def __init__(self, controller, name="Frequency Control"):
        super(FrequencyControls, self).__init__()

        self._updating_values = False
        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self.setTitle(name)

        grid = QtGui.QGridLayout()

        cfreq_bt, cfreq_txt = self._center_freq()
        grid.addWidget(cfreq_bt, 0, 0, 1, 1)
        grid.addWidget(cfreq_txt, 0, 1, 1, 1)

        bw_bt, bw_txt = self._bw_controls()
        grid.addWidget(bw_bt, 1, 0, 1, 1)
        grid.addWidget(bw_txt, 1, 1, 1, 1)

        fstart_bt, fstart_txt = self._fstart_controls()
        grid.addWidget(fstart_bt, 0, 3, 1, 1)
        grid.addWidget(fstart_txt, 0, 4, 1, 1)

        fstop_bt, fstop_txt = self._fstop_controls()
        grid.addWidget(fstop_bt, 1, 3, 1, 1)
        grid.addWidget(fstop_txt, 1, 4, 1, 1)

        freq_inc_steps = self._freq_incr()
        grid.addWidget(freq_inc_steps, 2, 1, 1, 4)

        grid.setColumnMinimumWidth(2, 10)

        self.setLayout(grid)


    def device_changed(self, dut):
        # to later calculate valid frequency values
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state
        if 'mode' in changed:
            min_tunable = float(self.dut_prop.MIN_TUNABLE[state.rfe_mode()])
            max_tunable = float(self.dut_prop.MAX_TUNABLE[state.rfe_mode()])
            tuning_res = float(self.dut_prop.TUNING_RESOLUTION)

            # XXX tuning_res is used here as an approximation of
            # "smallest reasonable span"
            self._freq_edit.setMinimum(min_tunable / M)
            self._freq_edit.setMaximum(max_tunable / M)
            self._fstart_edit.setMinimum(min_tunable / M)
            self._fstart_edit.setMaximum((max_tunable - tuning_res) / M)
            self._fstop_edit.setMinimum((min_tunable + tuning_res) / M)
            self._fstop_edit.setMaximum(max_tunable / M)
            self._bw_edit.setMinimum(tuning_res / M)
            self._bw_edit.setMaximum((max_tunable - min_tunable) / M)

            if state.mode in  ('IQIN', 'DD'):
                self._freq_edit.setText(str(min_tunable / M))
                self._freq_edit.setEnabled(False)
                self.update_freq_edit()
            else:
                self._bw_edit.setValue(float(
                    self.dut_prop.FULL_BW[state.rfe_mode()]) / M)
                self._freq_edit.setEnabled(True)

            if state.sweeping():
                self._fstart_edit.setEnabled(True)
                self._fstart.setEnabled(True)
                self._fstop.setEnabled(True)
                self._fstop_edit.setEnabled(True)
                self._bw.setEnabled(True)
                self._bw_edit.setEnabled(True)
            else:
                self._fstart_edit.setEnabled(False)
                self._fstart.setEnabled(False)
                self._fstop.setEnabled(False)
                self._fstop_edit.setEnabled(False)
                self._bw.setEnabled(False)
                self._bw_edit.setEnabled(False)

        if 'center' in changed or 'span' in changed:
            self._update_freq_edit()


    def _freq_incr(self):
        steps = QtGui.QComboBox(self)
        steps.addItem("Adjust: 1 MHz")
        steps.addItem("Adjust: 2.5 MHz")
        steps.addItem("Adjust: 10 MHz")
        steps.addItem("Adjust: 25 MHz")
        steps.addItem("Adjust: 100 MHz")
        self.fstep = float(steps.currentText().split()[1])
        def freq_step_change():
            self.fstep = float(steps.currentText().split()[1])
            self._freq_edit.setSingleStep(self.fstep)
            self._bw_edit.setSingleStep(self.fstep)
            self._fstart_edit.setSingleStep(self.fstep)
            self._fstop_edit.setSingleStep(self.fstep)
        steps.currentIndexChanged.connect(freq_step_change)
        steps.setCurrentIndex(2)
        self._fstep_box = steps
        return  steps

    def _center_freq(self):
        cfreq = QtGui.QLabel('Center:')
        self._cfreq = cfreq
        freq_edit = QtGui.QDoubleSpinBox()
        freq_edit.setMinimumHeight(SPIN_BOX_HEIGHT)
        freq_edit.setSuffix(' MHz')
        self._freq_edit = freq_edit
        def freq_change():
            if self._updating_values:
                return
            self.controller.apply_settings(center=freq_edit.value() * M)
        freq_edit.valueChanged.connect(freq_change)
        return cfreq, freq_edit

    def _bw_controls(self):
        bw = QtGui.QLabel('Span:')
        self._bw = bw
        bw_edit = QtGui.QDoubleSpinBox()
        bw_edit.setMinimumHeight(SPIN_BOX_HEIGHT)
        bw_edit.setSuffix(' MHz')
        def freq_change():
            if self._updating_values:
                return
            self.controller.apply_settings(span=bw_edit.value() * M)
        bw_edit.valueChanged.connect(freq_change)
        self._bw_edit = bw_edit
        return bw, bw_edit

    def _fstart_controls(self):
        fstart = QtGui.QLabel('Start:')
        self._fstart = fstart
        freq = QtGui.QDoubleSpinBox()
        freq.setMinimumHeight(SPIN_BOX_HEIGHT)
        freq.setSuffix(' MHz')
        def freq_change():
            if self._updating_values:
                return
            fstart = freq.value()
            fstop = self.gui_state.center + self.gui_state.span / 2.0
            self.controller.apply_settings(
                center = (fstop + fstart) / 2.0 * M,
                span = (fstop - fstart) * M,
                )
        freq.valueChanged.connect(freq_change)
        self._fstart_edit = freq
        return fstart, freq

    def _fstop_controls(self):
        fstop = QtGui.QLabel('Stop:')
        self._fstop = fstop
        freq = QtGui.QDoubleSpinBox()
        freq.setMinimumHeight(SPIN_BOX_HEIGHT)
        freq.setSuffix(' MHz')
        def freq_change():
            if self._updating_values:
                return
            fstart = self.gui_state.center - self.gui_state.span / 2.0
            fstop = freq.value()
            self.controller.apply_settings(
                center = (fstop + fstart) / 2.0 * M,
                span = (fstop - fstart) * M,
                )
        freq.valueChanged.connect(freq_change)
        self._fstop_edit = freq
        return fstop, freq

    def _update_freq_edit(self):
        """
        update the spin boxes from self.gui_state
        """
        self._updating_values = True

        center = float(self.gui_state.center) / M
        span = float(self.gui_state.span) / M
        self._fstop_edit.setValue(center + span / 2)
        self._fstart_edit.setValue(center - span / 2)
        self._freq_edit.setValue(center)
        self._bw_edit.setValue(span)

        self._updating_values = False

    def reset_freq_bounds(self):
            self.start_freq = None
            self.stop_freq = None

    def enable(self):
        self._bw.setEnabled(True)
        self._bw_edit.setEnabled(True)
        self._fstart.setEnabled(True)
        self._fstart_edit.setEnabled(True)
        self._fstop.setEnabled(True)
        self._fstop_edit.setEnabled(True)

    def disable(self):
        self._bw.setEnabled(False)
        self._bw_edit.setEnabled(False)
        self._fstart.setEnabled(False)
        self._fstart_edit.setEnabled(False)
        self._fstop.setEnabled(False)
        self._fstop_edit.setEnabled(False)

    def change_center_freq(self, freq):
        self._cfreq.click()
        self._freq_edit.setValue(freq / M)
        self.update_freq()
