from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors
from pyrf.gui.widgets import QDoubleSpinBoxPlayback
from pyrf.gui.fonts import GROUP_BOX_FONT

class FrequencyControls(QtGui.QGroupBox):

    def __init__(self, controller, name="Frequency Control"):
        super(FrequencyControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self.setTitle(name)
        self.setStyleSheet(GROUP_BOX_FONT)
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

        freq_inc_label, freq_inc_steps = self._freq_incr()
        grid.addWidget(freq_inc_label, 2, 0, 1, 1)
        grid.addWidget(freq_inc_steps, 2, 1, 1, 1)

        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 9)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 3)
        grid.setColumnStretch(4, 9)

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
            self._freq_edit.quiet_update(min_tunable / M, max_tunable / M)
            self._fstart_edit.quiet_update(
                min_tunable / M, (max_tunable - tuning_res) / M)
            self._fstop_edit.quiet_update(
                (min_tunable + tuning_res) / M, max_tunable / M)
            self._bw_edit.quiet_update(
                tuning_res / M, (max_tunable - min_tunable) / M)

            if state.sweeping():
                self._fstart_edit.setEnabled(not state.playback)
                self._fstop_edit.setEnabled(not state.playback)
                self._bw_edit.setEnabled(not state.playback)
            else:
                self._fstart_edit.setEnabled(False)
                self._fstop_edit.setEnabled(False)
                self._bw_edit.setEnabled(False)

        if any(x in changed for x in ('center', 'span', 'decimation', 'mode')):
            self._update_freq_edit()

        if 'playback' in changed:
            self._freq_edit.setEnabled(not state.playback)


    def _freq_incr(self):
        steps_label = QtGui.QLabel("Adjust:")
        steps = QtGui.QComboBox(self)
        steps.addItem("0.1 MHz")
        steps.addItem("0.2 MHz")
        steps.addItem("0.5 MHz")
        steps.addItem("1 MHz")
        steps.addItem("2 MHz")
        steps.addItem("5 MHz")
        steps.addItem("10 MHz")
        steps.addItem("20 MHz")
        steps.addItem("50 MHz")
        steps.addItem("100 MHz")
        self.fstep = float(steps.currentText().split()[0])
        def freq_step_change():
            self.fstep = float(steps.currentText().split()[0])
            self._freq_edit.setSingleStep(self.fstep)
            self._bw_edit.setSingleStep(self.fstep)
            self._fstart_edit.setSingleStep(self.fstep)
            self._fstop_edit.setSingleStep(self.fstep)
        steps.currentIndexChanged.connect(freq_step_change)
        steps.setCurrentIndex(6)
        self._fstep_box = steps
        return steps_label, steps

    def _center_freq(self):
        cfreq = QtGui.QLabel('Center:')
        self._cfreq = cfreq
        freq_edit = QDoubleSpinBoxPlayback()
        freq_edit.setSuffix(' MHz')
        self._freq_edit = freq_edit
        def freq_change():
            self.controller.apply_settings(center=freq_edit.value() * M)
            if self.gui_state.device_settings['iq_output_path'] == 'CONNECTOR':
                self.controller.apply_device_settings(freq = freq_edit.value() * M)
        freq_edit.valueChanged.connect(freq_change)
        return cfreq, freq_edit

    def _bw_controls(self):
        bw = QtGui.QLabel('Span:')
        self._bw = bw
        bw_edit = QDoubleSpinBoxPlayback()
        bw_edit.setSuffix(' MHz')
        def freq_change():
            self.controller.apply_settings(span=bw_edit.value() * M)
        bw_edit.valueChanged.connect(freq_change)
        self._bw_edit = bw_edit
        return bw, bw_edit

    def _fstart_controls(self):
        fstart = QtGui.QLabel('Start:')
        self._fstart = fstart
        freq = QDoubleSpinBoxPlayback()
        freq.setSuffix(' MHz')
        def freq_change():
            fstart = freq.value() * M
            fstop = self.gui_state.center + self.gui_state.span / 2.0
            fstop = max(fstop, fstart + self.dut_prop.TUNING_RESOLUTION)
            self.controller.apply_settings(
                center = (fstop + fstart) / 2.0,
                span = (fstop - fstart),
                )
        freq.valueChanged.connect(freq_change)
        self._fstart_edit = freq
        return fstart, freq

    def _fstop_controls(self):
        fstop = QtGui.QLabel('Stop:')
        self._fstop = fstop
        freq = QDoubleSpinBoxPlayback()
        freq.setSuffix(' MHz')
        def freq_change():
            fstart = self.gui_state.center - self.gui_state.span / 2.0
            fstop = freq.value() * M
            fstart = min(fstart, fstop - self.dut_prop.TUNING_RESOLUTION)
            self.controller.apply_settings(
                center = (fstop + fstart) / 2.0,
                span = (fstop - fstart),
                )
        freq.valueChanged.connect(freq_change)
        self._fstop_edit = freq
        return fstop, freq

    def _update_freq_edit(self):
        """
        update the spin boxes from self.gui_state
        """
        center = float(self.gui_state.center) / M
        span = float(self.gui_state.span) / M
        self._fstop_edit.quiet_update(value=center + span / 2)
        self._fstart_edit.quiet_update(value=center - span / 2)
        self._freq_edit.quiet_update(value=center)
        self._bw_edit.quiet_update(value=span)

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

