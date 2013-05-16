
"""
The main application window and GUI controls

``MainWindow`` creates and handles the ``File | Open Device`` menu and
wraps the ``MainPanel`` widget responsible for most of the interface.

All the buttons and controls and their callback functions are built in
``MainPanel`` and arranged on a grid.  A ``SpectrumView`` is created
and placed to left of the controls.
"""

import sys
import socket

from PySide import QtGui, QtCore
from util import frequency_text
from util import hotkey_util
import pyqtgraph as pg
import numpy as np

from pyrf.devices.thinkrf import WSA4000
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.util import read_data_and_context
from pyrf.config import TriggerSettings
from pyrf.numpy_util import compute_fft
from pyrf import twisted_util
import msvcrt

try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass

DEVICE_FULL_SPAN = 125e6
PLOT_YMIN = -130
PLOT_YMAX = 20
LNEG_NUM = -5000
LEVELED_TRIGGER_TYPE = 'LEVEL'
NONE_TRIGGER_TYPE = 'NONE'

class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, name=None):
        super(MainWindow, self).__init__()
        self.initUI()

        self.dut = None
        self._reactor = self._get_reactor()
        if len(sys.argv) > 1:
            self.open_device(sys.argv[1])
        else:
            self.open_device_dialog()
        self.show()

    def _get_reactor(self):
        # late import because installReactor is being used
        from twisted.internet import reactor
        return reactor

    def initUI(self):
        openAction = QtGui.QAction('&Open Device', self)
        openAction.triggered.connect(self.open_device_dialog)
        exitAction = QtGui.QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)

        self.setWindowTitle('PyRF')

    def open_device_dialog(self):
        name, ok = QtGui.QInputDialog.getText(self, 'Open Device',
            'Enter a hostname or IP address:')
        while True:
            if not ok:
                return

            try:
                self.open_device(name)
                break
            except socket.error:
                name, ok = QtGui.QInputDialog.getText(self, 'Open Device',
                    'Connection Failed, please try again\n\n'
                    'Enter a hostname or IP address:')

    @inlineCallbacks
    def open_device(self, name):
        # late import because installReactor is being used
        dut = WSA4000(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)
        if '--reset' in sys.argv:
            yield dut.reset()

        self.dut = dut
        self.setCentralWidget(MainPanel(dut))
        self.setWindowTitle('PyRF: %s' % name)

    def closeEvent(self, event):
        event.accept()
        self._reactor.stop()


class MainPanel(QtGui.QWidget):
    """
    The spectrum view and controls
    """
    def __init__(self, dut):
        super(MainPanel, self).__init__()
        self.dut = dut
        self.dut.reset()
        self.points = 1024
        self.grid_enable = True
        
        # max hold settings
        self.mhold_enable = False
        self.mhold_curve = None
        self.mhold_fft = None
        
        # trigger settings
        self.trig_enable = False
        self.trig_set = None
        self.amptrig_line = None
        self.freqtrig_lines = None

        self.mhz_bottom, self.mhz_top = (f/10**6 for f in dut.SWEEP_FREQ_RANGE)
        self.center_freq = None
        self.bandwidth = None
        self.decimation_factor = None
        self.decimation_points = None
        
        # plot window
        self.plot_window = pg.PlotWidget(name='Plot1')
        # initialize the x-axis of the plot
        self.plot_window.setXRange(2350e6,2450e6)
        self.plot_window.setLabel('bottom', text= 'Frequency', units = 'Hz', unitPrefix=None)
        self.plot_window.setYRange(PLOT_YMIN, PLOT_YMAX)
        self.plot_window.setLabel('left', text = 'Power', units = 'dBm')
        self.grid_control(self.grid_enable)
        self.fft_curve = self.plot_window.plot(pen = 'g')
        self.freq_range = None
        self.initDUT()
        self.initUI()

    @inlineCallbacks
    def initDUT(self):

        
        yield self.dut.request_read_perm()
        while True:
            data, context = yield twisted_util.read_data_and_context(
                self.dut, self.points)

            # compute FFT
            pow_data = compute_fft(self.dut, data, context)

            # grab center frequency/bandwidth to calculate axis width/height
            _center_freq = context['rffreq']
            _bandwidth = context['bandwidth']
            if (_center_freq != self.center_freq or _bandwidth != self.bandwidth):
                # update axes limits
                self.center_freq = _center_freq
                self.bandwidth = _bandwidth
                start_freq = (self.center_freq) - (self.bandwidth / 2)
                stop_freq = (self.center_freq) + (self.bandwidth / 2)

            else:
                start_freq = None
                stop_freq = None
            
            self.update_plot(pow_data,start_freq,stop_freq)
    
    # adjust the layout according to which key was pressed
    def keyPressEvent(self, event):

        hotkey_util(self, str(event.text()))
       
    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)

        grid.setColumnMinimumWidth(0, 400)
        grid.addWidget(self.plot_window,0,0,10,1)
      
        y = 0
        grid.addWidget(self._antenna_control(), y, 1, 1, 2)
        grid.addWidget(self._bpf_control(), y, 3, 1, 2)
        y += 1
        grid.addWidget(self._gain_control(), y, 1, 1, 2)
        grid.addWidget(QtGui.QLabel('IF Gain:'), y, 3, 1, 1)
        grid.addWidget(self._ifgain_control(), y, 4, 1, 1)
        y += 1
        freq, steps, freq_plus, freq_minus = self._freq_controls()
        grid.addWidget(QtGui.QLabel('Center Freq:'), y, 1, 1, 1)
        grid.addWidget(freq, y, 2, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), y, 4, 1, 1)
        y += 1
        grid.addWidget(steps, y, 2, 1, 2)
        grid.addWidget(freq_minus, y, 1, 1, 1)
        grid.addWidget(freq_plus, y, 4, 1, 1)
        y += 1
        span, rbw = self._span_rbw_controls()
        grid.addWidget(span, y, 1, 1, 2)
        grid.addWidget(rbw, y, 3, 1, 2)
        
        self.setLayout(grid)
        self.show()
          
    @inlineCallbacks
    def _read_update_antenna_box(self):
        ant = yield self.dut.antenna()
        self._antenna_box.setCurrentIndex(ant - 1)

    def _antenna_control(self):
        antenna = QtGui.QComboBox(self)
        antenna.addItem("Antenna 1")
        antenna.addItem("Antenna 2")
        self._antenna_box = antenna
        self._read_update_antenna_box()
        def new_antenna():
            self.dut.antenna(int(antenna.currentText().split()[-1]))
        antenna.currentIndexChanged.connect(new_antenna)
        return antenna

    @inlineCallbacks
    def _read_update_bpf_box(self):
        bpf = yield self.dut.preselect_filter()
        self._bpf_box.setCurrentIndex(0 if bpf else 1)

    def _bpf_control(self):
        bpf = QtGui.QComboBox(self)
        bpf.addItem("BPF On")
        bpf.addItem("BPF Off")
        self._bpf_box = bpf
        self._read_update_bpf_box()
        def new_bpf():
            self.dut.preselect_filter("On" in bpf.currentText())
        bpf.currentIndexChanged.connect(new_bpf)
        return bpf

    @inlineCallbacks
    def _read_update_gain_box(self):
        gain = yield self.dut.gain()
        self._gain_box.setCurrentIndex(self._gain_values.index(gain))

    def _gain_control(self):
        gain = QtGui.QComboBox(self)
        gain_values = ['High', 'Med', 'Low', 'VLow']
        for g in gain_values:
            gain.addItem("RF Gain: %s" % g)
        self._gain_values = [g.lower() for g in gain_values]
        self._gain_box = gain
        self._read_update_gain_box()
        def new_gain():
            g = gain.currentText().split()[-1].lower().encode('ascii')
            self.dut.gain(g)
        gain.currentIndexChanged.connect(new_gain)
        return gain

    @inlineCallbacks
    def _read_update_ifgain_box(self):
        ifgain = yield self.dut.ifgain()
        self._ifgain_box.setValue(int(ifgain))

    def _ifgain_control(self):
        ifgain = QtGui.QSpinBox(self)
        ifgain.setRange(-10, 34)
        ifgain.setSuffix(" dB")
        self._ifgain_box = ifgain
        self._read_update_ifgain_box()
        def new_ifgain():
            self.dut.ifgain(ifgain.value())
        ifgain.valueChanged.connect(new_ifgain)
        return ifgain

    @inlineCallbacks
    def _read_update_freq_edit(self):
        "Get current frequency from self.dut and update the edit box"
        self._update_freq_edit() # once immediately in case of long delay
        self.center_freq = yield self.dut.freq()
        self._update_freq_edit()

    def _update_freq_edit(self):
        "Update the frequency edit box from self.center_freq"
        if self.center_freq is None:
            self._freq_edit.setText("---")
        else:
            self._freq_edit.setText("%0.1f" % (self.center_freq / 1e6))

    def _freq_controls(self):
        freq = QtGui.QLineEdit("")
        self._freq_edit = freq
        self._read_update_freq_edit()
        def write_freq():
            try:
                f = float(freq.text())
            except ValueError:
                return
            if f < self.mhz_bottom:
                f = self.mhz_bottom
                self.set_freq_mhz(f)
                self._update_freq_edit()
            elif self.mhz_top < f:
                f = self.mhz_top
                self.set_freq_mhz(f)
                self._update_freq_edit()
            else:
                self.set_freq_mhz(f)
        freq.editingFinished.connect(write_freq)

        steps = QtGui.QComboBox(self)
        steps.addItem("Adjust: 1 MHz")
        steps.addItem("Adjust: 2.5 MHz")
        steps.addItem("Adjust: 10 MHz")
        steps.addItem("Adjust: 25 MHz")
        steps.addItem("Adjust: 100 MHz")
        steps.setCurrentIndex(2)
        def freq_step(factor):
            try:
                f = float(freq.text())
            except ValueError:
                self._update_freq_edit()
                return
            delta = float(steps.currentText().split()[1]) * factor
            freq.setText("%0.1f" % (f + delta))
            write_freq()
        freq_minus = QtGui.QPushButton('-')
        freq_minus.clicked.connect(lambda: freq_step(-1))
        freq_plus = QtGui.QPushButton('+')
        freq_plus.clicked.connect(lambda: freq_step(1))

        return freq, steps, freq_plus, freq_minus

    @inlineCallbacks
    def _read_update_span_rbw_boxes(self):
        self.decimation_factor = yield self.dut.decimation()
        self._span_box.setCurrentIndex(
            self._decimation_values.index(self.decimation_factor))
        self._update_rbw_box()

    def _update_rbw_box(self):
        d = self.decimation_factor
        for i, p in enumerate(self._points_values):
            r = DEVICE_FULL_SPAN / d / p
            self._rbw_box.setItemText(i, "RBW: %s" % frequency_text(r))
            if self.decimation_points and self.decimation_points == d * p:
                self._rbw_box.setCurrentIndex(i)
        self.points = self._points_values[self._rbw_box.currentIndex()]

    def _span_rbw_controls(self):
        span = QtGui.QComboBox(self)
        decimation_values = [1] + [2 ** x for x in range(2, 10)]
        for d in decimation_values:
            span.addItem("Span: %s" % frequency_text(DEVICE_FULL_SPAN / d))
        self._decimation_values = decimation_values
        self._span_box = span
        def new_span():
            self.set_decimation(decimation_values[span.currentIndex()])
            self._update_rbw_box()
        span.currentIndexChanged.connect(new_span)

        rbw = QtGui.QComboBox(self)
        self._points_values = [2 ** x for x in range(8, 16)]
        self._rbw_box = rbw
        rbw.addItems([str(p) for p in self._points_values])
        self._read_update_span_rbw_boxes()

        def new_rbw():
            self.points = self._points_values[rbw.currentIndex()]
            self.decimation_points = self.decimation_factor * self.points
        rbw.setCurrentIndex(self._points_values.index(1024))
        rbw.currentIndexChanged.connect(new_rbw)

        return span, rbw

    def set_freq_mhz(self, f):
        self.center_freq = f * 1e6
        self.dut.freq(self.center_freq)
        
        # reset max hold whenever frequency is changed
        self.mhold_fft = None

    def set_decimation(self, d):
        self.decimation_factor = 1 if d == 0 else d
        self.dut.decimation(d)
        
    def update_plot(self, pow_data, start_freq, stop_freq):

        if start_freq != None and stop_freq != None:
            # update the frequency range (Hz)
            self.freq_range = np.linspace(start_freq,stop_freq , len(pow_data))
       
        if self.mhold_enable:
        
            if (self.mhold_fft == None or 
                len(self.mhold_fft) != len(pow_data)):
                
                self.mhold_fft = np.zeros(len(pow_data)) + LNEG_NUM
                
            self.mhold_fft = np.maximum(self.mhold_fft,pow_data)
            self.mhold_curve.setData(self.freq_range,self.mhold_fft,pen = 'y')
        
        if (self.trig_enable == True and
            self.freqtrig_lines != None and
            self.amptrig_line != None):
            self.update_trig()
            
                
        # plot the standard FFT curve
        self.fft_curve.setData(self.freq_range,pow_data,pen = 'g')
    
    def grid_control(self,state):
        if state == True:
            self.plot_window.showGrid(x = True, y = True)
        elif state == False:
            self.plot_window.showGrid(x = False, y = False)

    def update_trig(self):
            amplitude = self.amptrig_line.value()
            freq_region = self.freqtrig_lines.getRegion()
            start_freq = min(freq_region)
            stop_freq = max(freq_region)
            if (start_freq != self.trig_set.fstart or
                stop_freq != self.trig_set.fstop or
                amplitude != self.trig_set.amplitude):
                self.trig_set = TriggerSettings(LEVELED_TRIGGER_TYPE, start_freq, stop_freq,amplitude) 
                self.dut.trigger(self.trig_set)

