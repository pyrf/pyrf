from PySide import QtGui

from pyrf.units import M
from pyrf.gui import colors


class FrequencyControls(QtGui.QGroupBox):

    def __init__(self, controller, name="Frequency Control"):
        super(FrequencyControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self.setTitle(name)

        self.freq_sel = 'CENT'

        freq_layout = QtGui.QVBoxLayout()

        fstart_hbox = QtGui.QHBoxLayout()
        fstart_bt, fstart_txt = self._fstart_controls()
        fstart_hbox.addWidget(fstart_bt)
        fstart_hbox.addWidget(fstart_txt)
        fstart_hbox.addWidget(QtGui.QLabel('MHz'))
        self._fstart_hbox = fstart_hbox

        cfreq_hbox = QtGui.QHBoxLayout()
        cfreq_bt, cfreq_txt = self._center_freq()
        cfreq_hbox.addWidget(cfreq_bt)
        cfreq_hbox.addWidget(cfreq_txt)
        cfreq_hbox.addWidget(QtGui.QLabel('MHz'))
        self._cfreq_hbox = cfreq_hbox

        bw_hbox = QtGui.QHBoxLayout()
        bw_bt, bw_txt = self._bw_controls()
        bw_hbox.addWidget(bw_bt)
        bw_hbox.addWidget(bw_txt)
        bw_hbox.addWidget(QtGui.QLabel('MHz'))
        self._bw_hbox = bw_hbox

        fstop_hbox = QtGui.QHBoxLayout()
        fstop_bt, fstop_txt = self._fstop_controls()
        fstop_hbox.addWidget(fstop_bt)
        fstop_hbox.addWidget(fstop_txt)
        fstop_hbox.addWidget(QtGui.QLabel('MHz'))
        self._fstop_hbox = fstop_hbox

        freq_inc_hbox = QtGui.QHBoxLayout()
        freq_inc_steps, freq_inc_plus, freq_inc_minus = self._freq_incr()
        freq_inc_hbox.addWidget(freq_inc_minus)
        freq_inc_hbox.addWidget(freq_inc_steps)
        freq_inc_hbox.addWidget(freq_inc_plus)
        self._freq_inc_hbox = freq_inc_hbox

        freq_layout.addLayout(self._fstart_hbox)
        freq_layout.addLayout(self._cfreq_hbox)
        freq_layout.addLayout(self._bw_hbox)
        freq_layout.addLayout(self._fstop_hbox)
        freq_layout.addLayout(self._freq_inc_hbox)
        self.setLayout(freq_layout)
        self._freq_layout = freq_layout


    def device_changed(self, dut):
        # to later calculate valid frequency values
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state
        if 'mode' in changed:
            min_tunable = self.dut_prop.MIN_TUNABLE[state.rfe_mode()]

            if state.mode in  ('IQIN', 'DD'):
                self._freq_edit.setText(str(min_tunable / M))
                self._freq_edit.setEnabled(False)
                self.update_freq_edit()
            else:
                self._bw_edit.setText(str(float(
                    self.dut_prop.FULL_BW[state.rfe_mode()]) / M))
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
            self._fstart_edit.setText(str(f / float(M)))
            f = state.center + (state.span / 2)
            self._fstop_edit.setText(str(f / float(M)))
            self._freq_edit.setText(str(state.center / float(M)))
            self._bw_edit.setText(str(state.span / float(M)))

        if 'decimation' in changed:
            self.update_freq()

    def _center_freq(self):
        cfreq = QtGui.QPushButton('Center')
        cfreq.setToolTip("[2]\nTune the center frequency") 
        self._cfreq = cfreq
        cfreq.clicked.connect(self.select_center)
        freq_edit = QtGui.QLineEdit()
        self._freq_edit = freq_edit
        def freq_change():
            self.select_center()
            self.update_freq()
            self.update_freq_edit()

        freq_edit.returnPressed.connect(freq_change)
        return cfreq, freq_edit

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
        steps.currentIndexChanged.connect(freq_step_change)
        steps.setCurrentIndex(2)
        self._fstep_box = steps
        def freq_step(factor):
            try:
                f = float(self._freq_edit.text())
            except ValueError:
                return
            delta = float(steps.currentText().split()[1]) * factor
            self.update_freq(delta)
            self.update_freq_edit()   
        freq_minus = QtGui.QPushButton('-')
        freq_minus.clicked.connect(lambda: freq_step(-1))
        self._freq_minus = freq_minus
        freq_plus = QtGui.QPushButton('+')
        freq_plus.clicked.connect(lambda: freq_step(1))
        self._freq_plus = freq_plus
        return  steps, freq_plus, freq_minus

    def _bw_controls(self):
        bw = QtGui.QPushButton('Span')
        bw.setToolTip("[3]\nChange the bandwidth of the current plot")
        self._bw = bw
        bw.clicked.connect(self.select_bw)
        bw_edit = QtGui.QLineEdit()
        def freq_change():
            self.select_bw()
            self.update_freq()
            self.update_freq_edit()
        bw_edit.returnPressed.connect(freq_change)
        self._bw_edit = bw_edit
        return bw, bw_edit

    def _fstart_controls(self):
        fstart = QtGui.QPushButton('Start')
        fstart.setToolTip("[1]\nTune the start frequency")
        self._fstart = fstart
        fstart.clicked.connect(self.select_fstart)
        freq = QtGui.QLineEdit()
        def freq_change():
            self.select_fstart()
            self.update_freq()
            self.update_freq_edit()

        freq.returnPressed.connect(freq_change)
        self._fstart_edit = freq
        return fstart, freq

    def _fstop_controls(self):
        fstop = QtGui.QPushButton('Stop')
        fstop.setToolTip("[4]Tune the stop frequency")
        self._fstop = fstop
        fstop.clicked.connect(self.select_fstop)
        freq = QtGui.QLineEdit()
        def freq_change():
            self.select_fstop()
            self.update_freq()
            self.update_freq_edit()
        freq.returnPressed.connect(freq_change)
        self._fstop_edit = freq
        return fstop, freq

    def update_freq(self, delta=0):
        min_tunable = self.dut_prop.MIN_TUNABLE[self.gui_state.rfe_mode()]
        max_tunable = self.dut_prop.MAX_TUNABLE[self.gui_state.rfe_mode()]
        try:
            if self.freq_sel == 'CENT':
                f = (float(self._freq_edit.text()) + delta) * M
                if f > max_tunable or f < min_tunable:
                    return
                self.update_freq_set(fcenter = f)
            elif self.freq_sel == 'FSTART':
                f = (float(self._fstart_edit.text()) + delta) * M
                if f > max_tunable or f <min_tunable or f > self.fstop:
                    return
                self.update_freq_set(fstart = f)

            elif self.freq_sel == 'FSTOP':

                f = (float(self._fstop_edit.text()) + delta) * M

                if f > max_tunable or f < min_tunable or f < self.fstart:
                    print f, self._fstart, max_tunable, min_tunable
                    return
                self.update_freq_set(fstop = f)

            elif self.freq_sel == 'BW':
                f = (float(self._bw_edit.text()) + delta) * M
                if self.gui_state.center - (f / 2) < min_tunable or self.gui_state.center + (f / 2) > max_tunable:
                    return
                self.update_freq_set(bw = f)
        except ValueError:
            return

    def update_freq_edit(self):
        self._fstop_edit.setText("%0.2f" % (self.fstop/ M))
        self._fstart_edit.setText("%0.2f" % (self.fstart/ M))
        self._freq_edit.setText("%0.2f" % (self.gui_state.center / M))
        self._bw_edit.setText("%0.2f" % (self.gui_state.span / M))

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

    def select_fstart(self):
        """
        changes the color of the fstart button to orange and all others to default
        """
        self._fstart.setStyleSheet(
            'background-color: %s; color: white;' % colors.ORANGE)
        self._cfreq.setStyleSheet("")
        self._fstop.setStyleSheet("")
        self._bw.setStyleSheet("")
        self.freq_sel = 'FSTART'

    def select_center(self):
        """
        changes the color of the fcenter button to orange and all others to default
        """
        self._cfreq.setStyleSheet(
            'background-color: %s; color: white;' % colors.ORANGE)
        self._fstart.setStyleSheet("")
        self._fstop.setStyleSheet("")
        self._bw.setStyleSheet("")
        self.freq_sel = 'CENT'

    def select_bw(self):
        """
        changes the color of the span button to orange and all others to default
        """
        self._bw.setStyleSheet(
            'background-color: %s; color: white;' % colors.ORANGE)
        self._fstart.setStyleSheet("")
        self._cfreq.setStyleSheet("")
        self._fstop.setStyleSheet("")
        self.freq_sel = 'BW'

    def select_fstop(self):
        """
        changes the color of the fstop button to orange and all others to default
        """
        self._fstop.setStyleSheet(
            'background-color: %s; color: white;' % colors.ORANGE)
        self._fstart.setStyleSheet("")
        self._cfreq.setStyleSheet("")
        self._bw.setStyleSheet("")
        self.freq_sel = 'FSTOP'

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


