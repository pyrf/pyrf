from PySide import QtGui


class FrequencyControls(QtGui.QGroupBox):

    def __init__(self, controller, name="Frequency Control"):
        super(FrequencyControls, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self.setTitle(name)

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

        self.update_freq()

    def device_changed(self, state, dut):
        # to later calculate valid frequency values
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        if 'mode' in changed:
            if state.mode == 'IQIN' or state.mode == 'DD':
                self._freq_edit.setText(str(
                    self.dut_prop.MIN_TUNABLE[state.rfe_mode()] / M))
                self._freq_edit.setEnabled(False)
                self.plot_state.update_freq_set(
                    fcenter=self.dut_prop.MIN_TUNABLE[state.rfe_mode()])
            else:
                self._bw_edit.setText(str(float(
                    self.dut_prop.FULL_BW[state.mode]) / M))
                self.plot_state.update_freq_set(
                    bw=self.dut_prop.FULL_BW[state.mode])
            self.update_freq_edit()

        if 'center' in changed or 'span' in changed:
            f = state.center - (state.span / 2)
            self._fstart_edit.setText(str(f / float(M)))
            f = state.center + (state.span / 2)
            self._fstop_edit.setText(str(f / float(M)))
            self._freq_edit.setText(str(state.center / float(M)))
            self._bw_edit.setText(str(state.span / float(M)))


    def _center_freq(self):
        cfreq = QtGui.QPushButton('Center')
        cfreq.setToolTip("[2]\nTune the center frequency") 
        self._cfreq = cfreq
        cfreq.clicked.connect(lambda: cu._select_center_freq(self))
        freq_edit = QtGui.QLineEdit()
        self._freq_edit = freq_edit
        def freq_change():
            cu._select_center_freq(self)
            self.update_freq()
            self.update_freq_edit()

        freq_edit.returnPressed.connect(lambda: freq_change())
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
        bw.clicked.connect(lambda: cu._select_bw(self))
        bw_edit = QtGui.QLineEdit()
        def freq_change():
            cu._select_bw(self)
            self.update_freq()
            self.update_freq_edit()
        bw_edit.returnPressed.connect(lambda: freq_change())
        self._bw_edit = bw_edit
        return bw, bw_edit

    def _fstart_controls(self):
        fstart = QtGui.QPushButton('Start')
        fstart.setToolTip("[1]\nTune the start frequency")
        self._fstart = fstart
        fstart.clicked.connect(lambda: cu._select_fstart(self))
        freq = QtGui.QLineEdit()
        def freq_change():
            cu._select_fstart(self)
            self.update_freq()
            self.update_freq_edit()

        freq.returnPressed.connect(lambda: freq_change())
        self._fstart_edit = freq
        return fstart, freq

    def _fstop_controls(self):
        fstop = QtGui.QPushButton('Stop')
        fstop.setToolTip("[4]Tune the stop frequency")
        self._fstop = fstop
        fstop.clicked.connect(lambda: cu._select_fstop(self))
        freq = QtGui.QLineEdit()
        def freq_change():
            cu._select_fstop(self)
            self.update_freq()
            self.update_freq_edit()
        freq.returnPressed.connect(lambda: freq_change())
        self._fstop_edit = freq
        return fstop, freq

    def update_freq(self, delta=None):
        rfe_mode = self.plot_state.dev_set['rfe_mode']
        min_tunable = self.dut_prop.MIN_TUNABLE[rfe_mode]
        max_tunable = self.dut_prop.MAX_TUNABLE[rfe_mode]
        if delta == None:
            delta = 0
        try:
            if self.plot_state.freq_sel == 'CENT':
                f = (float(self._freq_edit.text()) + delta) * M
                if f > max_tunable or f < min_tunable:
                    return
                self.plot_state.update_freq_set(fcenter = f)
                self.cap_dut.configure_device(self.plot_state.dev_set)
            elif self.plot_state.freq_sel == 'FSTART':
                f = (float(self._fstart_edit.text()) + delta) * M
                if f > max_tunable or f <min_tunable or f > self.plot_state.fstop:
                    return
                self.plot_state.update_freq_set(fstart = f)
            
            elif self.plot_state.freq_sel == 'FSTOP': 
                f = (float(self._fstop_edit.text()) + delta) * M

                if f > max_tunable or f < min_tunable or f < self.plot_state.fstart:
                    return
                self.plot_state.update_freq_set(fstop = f)
            
            elif self.plot_state.freq_sel == 'BW':
                f = (float(self._bw_edit.text()) + delta) * M
                if self.plot_state.center_freq - (f / 2) < min_tunable or self.plot_state.center_freq + (f / 2) > max_tunable:
                    return
                self.plot_state.update_freq_set(bw = f)
            for trace in self._plot.traces:
                try:
                    trace.data = self.pow_data
                except AttributeError:
                    break

        except ValueError:
            return
        if self.plot_state.trig:
            freq_region = self._plot.freqtrig_lines.getRegion()
            if (freq_region[0] < self.plot_state.fstart and freq_region[1] < self.plot_state.fstart) or (freq_region[0] > self.plot_state.fstop and freq_region[1] > self.plot_state.fstop):
                self._plot.freqtrig_lines.setRegion([self.plot_state.fstart,self.plot_state. fstop]) 

    def update_freq_edit(self):
        self._fstop_edit.setText("%0.1f" % (self.plot_state.fstop/ M))
        self._fstart_edit.setText("%0.1f" % (self.plot_state.fstart/ M))
        self._freq_edit.setText("%0.1f" % (self.plot_state.center_freq / M))
        self._bw_edit.setText("%0.1f" % (self.plot_state.bandwidth / M))
        self._center_bt.click()

