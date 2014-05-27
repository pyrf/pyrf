from PySide import QtGui

M = 1e6
INIT_CENTER_FREQ = 2450 * M
INIT_BANDWIDTH = 125 * M
INIT_RBW = 244141
RBW_VALUES = [976.562, 488.281, 244.141, 122.070, 61.035, 30.518, 15.259, 7.62939, 3.815]
HDR_RBW_VALUES = [1271.56, 635.78, 317.890, 158.94, 79.475, 39.736, 19.868, 9.934]

class FrequencyControlsWidget(QtGui.QGroupBox):

    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to control the WSA4000/WSA5000
    :param name: The name of the groupBox
    
    Note: All the widgets inside this groupBox are not connected to any controls, and must be
    connected within the parent layout.
"""
    def __init__(self):
    
        super(FrequencyControlsWidget, self).__init__()
        self.center_freq = INIT_CENTER_FREQ
        self.bandwidth = INIT_BANDWIDTH 
        self.fstart = self.center_freq - self.bandwidth / 2
        self.fstop = self.center_freq + self.bandwidth / 2
        self.rbw = INIT_RBW 
        
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

        rbw_hbox = QtGui.QHBoxLayout()
        rbw = self._rbw_controls()
        rbw_hbox.addWidget(QtGui.QLabel('Resolution Bandwidth:'))
        rbw_hbox.addWidget(rbw)
        self._rbw_hbox = rbw_hbox
        self._rbw_box.setCurrentIndex(3)
        
        freq_layout.addLayout(self._fstart_hbox)
        freq_layout.addLayout(self._cfreq_hbox)
        freq_layout.addLayout(self._bw_hbox)
        freq_layout.addLayout(self._fstop_hbox)
        freq_layout.addLayout(self._freq_inc_hbox)
        freq_layout.addLayout(self._rbw_hbox)
        self.setLayout(freq_layout)
        self._freq_layout = freq_layout

    
    def _center_freq(self):
        cfreq = QtGui.QLabel('Center')
        cfreq.setToolTip("[2]\nTune the center frequency") 
        self._cfreq = cfreq
        freq_edit = QtGui.QLineEdit(str(INIT_CENTER_FREQ / float(M)))
        self._freq_edit = freq_edit
        return cfreq, freq_edit

    def _freq_incr(self):

        steps = QtGui.QComboBox()
        steps.addItem("Adjust: 1 MHz")
        steps.addItem("Adjust: 2.5 MHz")
        steps.addItem("Adjust: 10 MHz")
        steps.addItem("Adjust: 25 MHz")
        steps.addItem("Adjust: 100 MHz")
        self.fstep = float(steps.currentText().split()[1])

        steps.setCurrentIndex(2)
        self._fstep_box = steps
        freq_minus = QtGui.QPushButton('-')
        self._freq_minus = freq_minus
        freq_plus = QtGui.QPushButton('+')
        self._freq_plus = freq_plus
        return  steps, freq_plus, freq_minus

    def _bw_controls(self):
        bw = QtGui.QLabel('Span')
        bw.setToolTip("[3]\nChange the bandwidth of the current plot")
        self._bw = bw
        bw_edit = QtGui.QLineEdit(str(INIT_BANDWIDTH / float(M)))
        self._bw_edit = bw_edit
        return bw, bw_edit

    def _fstart_controls(self):
        fstart = QtGui.QLabel('Start')
        fstart.setToolTip("[1]\nTune the start frequency")
        self._fstart = fstart
        f = INIT_CENTER_FREQ - (INIT_BANDWIDTH / 2)
        freq = QtGui.QLineEdit(str(f / float(M)))
        self._fstart_edit = freq
        return fstart, freq

    def _fstop_controls(self):
        fstop = QtGui.QLabel('Stop')
        fstop.setToolTip("[4]Tune the stop frequency") 
        self._fstop = fstop
        f = INIT_CENTER_FREQ + (INIT_BANDWIDTH / 2)
        freq = QtGui.QLineEdit(str(f / float(M)))

        self._fstop_edit = freq
        return fstop, freq

    def _rbw_controls(self):
        rbw = QtGui.QComboBox()
        rbw.setToolTip("Change the RBW of the FFT plot")
        self._points_values = RBW_VALUES
        self._hdr_points_values = HDR_RBW_VALUES
        self._rbw_box = rbw
        rbw.addItems([str(p) + ' KHz' for p in self._points_values])
        rbw.setCurrentIndex(0)

        return rbw

            
            