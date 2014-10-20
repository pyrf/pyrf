from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors
from pyrf.gui.widgets import QComboBoxPlayback, QDoubleSpinBoxPlayback
from pyrf.gui.fonts import GROUP_BOX_FONT

MAXIMUM_WIDTH = 400
MAXIMUM_HEIGHT = 130

# FIXME: move to device properties?
MODE_TO_TEXT = {
    'Sweep SH': 'Sweep',
    'Sweep ZIF': 'Sweep (100 MHz steps)',
    'ZIF': '100 MHz span',
    'SH': '40 MHz span',
    'SHN': '10 MHz span',
    'HDR': '0.1 MHz span (high dynamic range)',
    'DD': '0 to 50 MHz (no tuning)',
    'IQIN': 'IQ input 100 MHz span (no tuning)',
}
TEXT_TO_MODE = dict((m,t) for (t,m) in MODE_TO_TEXT.iteritems())

class FrequencyControls(QtGui.QWidget):

    def __init__(self, controller):
        super(FrequencyControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self.setMaximumSize(MAXIMUM_WIDTH,MAXIMUM_HEIGHT)

        grid = QtGui.QGridLayout()

        mode_label, mode = self._input_mode()
        grid.addWidget(mode_label, 0, 0, 1, 1)
        grid.addWidget(mode, 0, 1, 1, 4)

        cfreq_bt, cfreq_txt = self._center_freq()
        grid.addWidget(cfreq_bt, 1, 0, 1, 1)
        grid.addWidget(cfreq_txt, 1, 1, 1, 1)

        bw_bt, bw_txt = self._bw_controls()
        grid.addWidget(bw_bt, 2, 0, 1, 1)
        grid.addWidget(bw_txt, 2, 1, 1, 1)

        fstart_bt, fstart_txt = self._fstart_controls()
        grid.addWidget(fstart_bt, 1, 3, 1, 1)
        grid.addWidget(fstart_txt, 1, 4, 1, 1)

        fstop_bt, fstop_txt = self._fstop_controls()
        grid.addWidget(fstop_bt, 2, 3, 1, 1)
        grid.addWidget(fstop_txt, 2, 4, 1, 1)

        freq_inc_label, freq_inc_steps = self._freq_incr()
        grid.addWidget(freq_inc_label, 3, 0, 1, 1)
        grid.addWidget(freq_inc_steps, 3, 1, 1, 1)

        rbw_label, rbw_combo = self._rbw_controls()
        grid.addWidget(rbw_label, 3, 3, 1, 1)
        grid.addWidget(rbw_combo, 3, 4, 1, 1)

        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 9)
        grid.setColumnStretch(2, 1)
        grid.setColumnStretch(3, 3)
        grid.setColumnStretch(4, 9)

        grid.setRowStretch(4, 1) # expand empty space at the bottom

        self.setLayout(grid)


    def device_changed(self, dut):
        # to later calculate valid frequency values
        self.dut_prop = dut.properties
        self._update_modes()

    def state_changed(self, state, changed):
        self.gui_state = state

        if state.playback:
            # for playback simply update on every state change
            self._mode.playback_value(MODE_TO_TEXT[state.mode])

        def enable_disable_edit_boxes():
            if state.sweeping():
                self._fstart_edit.setEnabled(not state.playback)
                self._fstop_edit.setEnabled(not state.playback)
                self._bw_edit.setEnabled(not state.playback)
            else:
                self._fstart_edit.setEnabled(False)
                self._fstop_edit.setEnabled(False)
                self._bw_edit.setEnabled(False)

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

            enable_disable_edit_boxes()
            self._update_rbw_options()

            if min_tunable == max_tunable:
                self._freq_edit.setEnabled(False)
                self._fstep_box.setEnabled(False)
            else:
                self._freq_edit.setEnabled(True)
                self._fstep_box.setEnabled(True)

        if any(x in changed for x in ('center', 'span', 'decimation', 'mode')):
            self._update_freq_edit()

        if 'playback' in changed:
            self._update_modes(current_mode=state.mode)
            self._freq_edit.setEnabled(not state.playback)
            if state.playback:
                self._rbw_box.playback_value(str(state.rbw))
            else:
                self._rbw_box.setEnabled(True)
            enable_disable_edit_boxes()
            self._update_rbw_options()

        if 'device_settings.iq_output_path' in changed:
            if state.device_settings['iq_output_path'] == 'CONNECTOR':
                self._update_modes(include_sweep=False)
                self._fstart_edit.setEnabled(False)
                self._fstop_edit.setEnabled(False)
                self._bw_edit.setEnabled(False)
                self._rbw_box.setEnabled(False)
            elif state.device_settings['iq_output_path'] == 'DIGITIZER':
                self._update_modes()
                self._rbw_box.setEnabled(True)

    def _input_mode(self):
        self._mode_label = QtGui.QLabel('Mode:')
        self._mode = QComboBoxPlayback()
        self._mode.setToolTip("Change the device input mode")

        def new_input_mode():
            input_mode = TEXT_TO_MODE[self._mode.currentText()]
            if not input_mode:
                return
            self.controller.apply_settings(mode=input_mode)
            #FIXME rfe_mode should not be in device settings dictionary
            if self.gui_state.device_settings['iq_output_path'] == 'CONNECTOR':
                self.controller.apply_device_settings(rfe_mode = input_mode)
        self._mode.currentIndexChanged.connect(new_input_mode)
        return self._mode_label, self._mode

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
        freq_edit.editingFinished.connect(freq_change)
        return cfreq, freq_edit

    def _bw_controls(self):
        bw = QtGui.QLabel('Span:')
        self._bw = bw
        bw_edit = QDoubleSpinBoxPlayback()
        bw_edit.setSuffix(' MHz')
        def freq_change():
            self.controller.apply_settings(span=bw_edit.value() * M)
        bw_edit.editingFinished.connect(freq_change)
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
        freq.editingFinished.connect(freq_change)
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
        freq.editingFinished.connect(freq_change)
        self._fstop_edit = freq
        return fstop, freq

    def _rbw_controls(self):
        rbw_label = QtGui.QLabel('RBW:')
        rbw_box = QComboBoxPlayback()
        rbw_box.setToolTip("Change the RBW of the FFT plot")
        def new_rbw():
            self.controller.apply_settings(rbw=self._rbw_values[
                rbw_box.currentIndex()])
        rbw_box.currentIndexChanged.connect(new_rbw)
        self._rbw_box = rbw_box
        return rbw_label, rbw_box


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

    def _rbw_replace_items(self, items):
        for i in range(self._rbw_box.count()):
            self._rbw_box.removeItem(0)
        self._rbw_box.addItems(items)

    def _update_rbw_options(self):
        """
        populate RBW drop-down with reasonable values for the current mode
        """
        if hasattr(self, 'gui_state'):
            mode = self.gui_state.rfe_mode()

            self._rbw_values = self.dut_prop.RBW_VALUES[mode]
            if mode == 'HDR':
                unit = 'Hz'
                div = 1
            else:
                unit = 'KHz'
                div = 1000
            self._rbw_box.quiet_update(
                ["%0.2f " % (float(p) / div) + unit for p in self._rbw_values])

            self._rbw_box.setCurrentIndex(self._rbw_box.count() - 1)

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

