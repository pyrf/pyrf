from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors

SPIN_BOX_HEIGHT = 40


class FrequencyControls(QtGui.QGroupBox):

    def __init__(self, controller, name="Frequency Control"):
        super(FrequencyControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self.setTitle(name)

        self.freq_sel = 'CENT'

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
                self.update_freq_set(
                    bw=self.dut_prop.FULL_BW[state.rfe_mode()])
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

            f = state.center - (state.span / 2)
            self._fstart_edit.setValue(float(f) / M)
            f = state.center + (state.span / 2)
            self._fstop_edit.setValue(float(f) / M)
            self._freq_edit.setValue(float(state.center) / M)
            self._bw_edit.setValue(float(state.span) / M)

        if 'decimation' in changed:
            self.update_freq()

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
            self.update_freq()
            self.update_freq_edit()

        freq_edit.valueChanged.connect(freq_change)
        return cfreq, freq_edit

    def _bw_controls(self):
        bw = QtGui.QLabel('Span:')
        self._bw = bw
        bw_edit = QtGui.QDoubleSpinBox()
        bw_edit.setMinimumHeight(SPIN_BOX_HEIGHT)
        bw_edit.setSuffix(' MHz')
        def freq_change():
            self.update_freq()
            self.update_freq_edit()
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
            self.update_freq()
            self.update_freq_edit()

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
            self.update_freq()
            self.update_freq_edit()
        freq.valueChanged.connect(freq_change)
        self._fstop_edit = freq
        return fstop, freq

    def update_freq(self, delta=0):
        min_tunable = self.dut_prop.MIN_TUNABLE[self.gui_state.rfe_mode()]
        max_tunable = self.dut_prop.MAX_TUNABLE[self.gui_state.rfe_mode()]
        try:
            if self.freq_sel == 'CENT':
                f = (float(self._freq_edit.value()) + delta) * M
                if f > max_tunable or f < min_tunable:
                    return
                self.update_freq_set(fcenter = f)
            elif self.freq_sel == 'FSTART':
                f = (float(self._fstart_edit.value()) + delta) * M
                if f > max_tunable or f <min_tunable or f > self.fstop:
                    return
                self.update_freq_set(fstart = f)

            elif self.freq_sel == 'FSTOP':

                f = (float(self._fstop_edit.value()) + delta) * M

                if f > max_tunable or f < min_tunable or f < self.fstart:
                    print f, self._fstart, max_tunable, min_tunable
                    return
                self.update_freq_set(fstop = f)

            elif self.freq_sel == 'BW':
                f = (float(self._bw_edit.value()) + delta) * M
                if self.gui_state.center - (f / 2) < min_tunable or self.gui_state.center + (f / 2) > max_tunable:
                    return
                self.update_freq_set(bw = f)
        except ValueError:
            return

    def update_freq_edit(self):
        self._fstop_edit.setValue(self.fstop / M)
        self._fstart_edit.setValue(self.fstart/ M)
        self._freq_edit.setValue(self.gui_state.center / M)
        self._bw_edit.setValue(self.gui_state.span / M)

    def update_freq_set(self,
                          fstart=None,
                          fstop=None,
                          fcenter=None,
                          bw=None):
        prop = self.dut_prop
        rfe_mode = self.gui_state.rfe_mode()
        min_tunable = prop.MIN_TUNABLE[rfe_mode]
        max_tunable = prop.MAX_TUNABLE[rfe_mode]
        if fcenter is not None:

            if not self.gui_state.sweeping():
                self.bandwidth = prop.FULL_BW[rfe_mode]
                self.fstart = fcenter - ((self.bandwidth / 2)) / self.gui_state.decimation
                self.fstop =  fcenter + (self.bandwidth / 2) / self.gui_state.decimation
                self.controller.apply_settings(center=fcenter)

                return

            self.fstart = max(min_tunable, fcenter - (self.bandwidth / 2))
            self.fstop = min(max_tunable, fcenter + (self.bandwidth / 2))
            self.bandwidth = (self.fstop - self.fstart)
            fcenter = self.fstart + (self.bandwidth / 2)
            self.bin_size = max(1, int((self.bandwidth) / self.gui_state.rbw))
            self.controller.apply_settings(center=fcenter, span=self.bandwidth)

        elif fstart is not None:
            fstart = min(fstart, self.fstop - prop.TUNING_RESOLUTION)
            self.fstart = fstart
            self.bandwidth = (self.fstop - self.fstart)
            fcenter = fstart + (self.bandwidth / 2)
            self.bin_size = max(1, int((self.bandwidth) / self.gui_state.rbw))
            self.controller.apply_settings(center=fcenter, span=self.bandwidth)

        elif fstop is not None:
            fstop = max(fstop, self.fstart + prop.TUNING_RESOLUTION)
            self.fstop = fstop
            self.bandwidth = (self.fstop - self.fstart)
            fcenter = fstop - (self.bandwidth / 2)
            self.bin_size = max(1, int((self.bandwidth) / self.gui_state.rbw))
            self.controller.apply_settings(center=fcenter, span=self.bandwidth)

        elif bw is not None:
            self.fstart =  self.gui_state.center - (bw / 2)
            self.fstop = self.gui_state.center + (bw / 2)
            self.bandwidth = (self.fstop - self.fstart)
            fcenter = self.fstart + (self.bandwidth / 2)
            self.bin_size = max(1, int((self.bandwidth) / self.gui_state.rbw))
            self.controller.apply_settings(center=fcenter, span=self.bandwidth)

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
