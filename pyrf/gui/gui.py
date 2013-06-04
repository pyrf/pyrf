
"""
The main application window and GUI controls

``MainWindow`` creates and handles the ``File | Open Device`` menu and
wraps the ``MainPanel`` widget responsible for most of the interface.

All the buttons and controls and their callback functions are built in
``MainPanel`` and arranged on a grid.  A ``Pyqtgraph Window`` is created
and placed to left of the controls.
"""

import sys
from PySide import QtGui, QtCore
import numpy as np

from contextlib import contextmanager
from util import frequency_text, find_max_index, find_nearest_index
from util import hotkey_util
import constants
import control_util as cu
from plot_widget import plot
import gui_config


from pyrf.gui.util import frequency_text
from pyrf.devices.thinkrf import WSA4000
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.util import read_data_and_context
from pyrf.config import TriggerSettings
from pyrf.numpy_util import compute_fft

try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass

class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, name=None):
        super(MainWindow, self).__init__()
        self.initUI()

        self.setWindowIcon(QtGui.QIcon("thinkrf_ico.png"))
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
        dut = WSA4000(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)
        if '--reset' in sys.argv:
            yield dut.reset()
        else:
            yield dut.flush()

        self.dut = dut
        self.setCentralWidget(MainPanel(dut))
        self.setMinimumWidth(920)
        self.setMinimumHeight(300)
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
                
        self.plot_state = gui_config.plot_state()

        # plot window
        self._plot = plot(self)
        self.mhz_bottom, self.mhz_top = (f/10**6 for f in dut.SWEEP_FREQ_RANGE)
        self._vrt_context = {}
        self.initDUT()
        self.initUI()

    @inlineCallbacks
    def initDUT(self):
        yield self.dut.request_read_perm()
        self.plot_state.center_freq = yield self.dut.freq()
        self.decimation_factor = yield self.dut.decimation()

        yield self.dut.flush()
        yield self.dut.request_read_perm()
        self.dut.connector.vrt_callback = self.receive_vrt
        yield self.dut.capture(self.plot_state.points, 1)

    def receive_vrt(self, packet):

        if packet.is_data_packet():
            if any(x not in self._vrt_context for x in (
                    'reflevel', 'rffreq', 'bandwidth')):
                return
            
            # queue up the next capture while we update
            self.dut.capture(self.plot_state.points, 1)
            
            # compute FFT
            pow_data = compute_fft(self.dut, packet, self._vrt_context)
            if self.plot_state.enable_plot:
                self.plot_state._pow = pow_data
            
            # grab center frequency/bandwidth to calculate axis width/height
            self.plot_state.center_freq = self._vrt_context['rffreq']
            self.plot_state.bandwidth = self._vrt_context['bandwidth']
            
            
            start_freq = (self.plot_state.center_freq) - (self.plot_state.bandwidth / 2)
            stop_freq = (self.plot_state.center_freq) + (self.plot_state.bandwidth / 2)

            self.update_plot(pow_data,start_freq,stop_freq)
        else:
            self._vrt_context.update(packet.fields)


    def keyPressEvent(self, event):
        hotkey_util(self, event)
        
    def mousePressEvent(self, event):

    
        click_pos =  event.pos().x() - 68
        plot_window_width = self._plot.window.width() - 68

        if click_pos < plot_window_width and click_pos > 0:

            window_freq = self._plot.view_box.viewRange()[0]
            window_bw =  (window_freq[1] - window_freq[0])
            click_freq = ((float(click_pos) / float(plot_window_width)) * float(window_bw)) + window_freq[0]

            if self.plot_state.marker_sel:
                self.plot_state.marker_ind  = find_nearest_index(click_freq, self.plot_state.freq_range)
            
            elif self.plot_state.delta_sel:
                self.plot_state.delta_ind = find_nearest_index(click_freq, self.plot_state.freq_range)
            
    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        grid.setColumnMinimumWidth(0, 400)
        
        # add plot widget
        grid.addWidget(self._plot.window,0,0,10,1)
                
        y = 0
        
        trig = self._trigger_control()
        grid.addWidget(trig, y, 1, 1, 1)
        mark = self._marker_control()
        grid.addWidget(mark, y, 2, 1, 1)
        delta = self._delta_control()
        grid.addWidget(delta, y, 3, 1, 1)
        peak = self._peak_control()
        grid.addWidget(peak, y, 4, 1, 1)
        
        y += 1
        mhold = self._mhold_control()
        grid.addWidget(mhold, y, 1, 1, 1)
        
        y += 1
        grid.addWidget(self._antenna_control(), y, 1, 1, 2)
        grid.addWidget(self._bpf_control(), y, 3, 1, 2)
        
        y += 1
        grid.addWidget(self._gain_control(), y, 1, 1, 2)
        grid.addWidget(QtGui.QLabel('IF Gain:'), y, 3, 1, 1)
        grid.addWidget(self._ifgain_control(), y, 4, 1, 1)
        
        y += 1
        fstart_bt, fstart_txt = self._fstart_controls()
        grid.addWidget(fstart_bt, y, 1, 1, 1)
        grid.addWidget(fstart_txt, y, 2, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), y, 4, 1, 1)
        
        y += 1
        cfreq, freq, steps, freq_plus, freq_minus = self._freq_controls()
        grid.addWidget(cfreq, y, 1, 1, 1)
        grid.addWidget(freq, y, 2, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), y, 4, 1, 1)
        
        y += 1
        fstop_bt, fstop_txt = self._fstop_controls()
        grid.addWidget(fstop_bt, y, 1, 1, 1)
        grid.addWidget(fstop_txt, y, 2, 1, 2)
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
    
    def _trigger_control(self):
        trigger = QtGui.QPushButton('(T)rigger', self)
        trigger.clicked.connect(lambda: cu._trigger_control(self))
        self._trigger = trigger
        return trigger
    
    def _marker_control(self):
        marker = QtGui.QPushButton('(M)arker 1', self)
        marker.clicked.connect(lambda: cu._marker_control(self))
        self._marker = marker
        return marker
        
    def _delta_control(self):
        delta = QtGui.QPushButton('Mar(k)er 2', self)
        delta.clicked.connect(lambda: cu._delta_control(self))
        self._delta = delta
        return delta
    
    def _peak_control(self):
        peak = QtGui.QPushButton('(P)eak', self)
        peak.clicked.connect(lambda: cu._find_peak(self))
        self._peak = peak
        return peak
        
    def _mhold_control(self):
        mhold = QtGui.QPushButton('Max (H)old', self)
        mhold.clicked.connect(lambda: cu._mhold_control(self))
        self._mhold = mhold
        return mhold
        
    def _grid_control(self):
        plot_grid = QtGui.QPushButton('(G)rid', self)
        plot_grid.clicked.connect(lambda: cu._grid_control(self))
        self._plot_grid = plot_grid
        return plot_grid

    def _center_control(self):
        center = QtGui.QPushButton('(C)enter View', self)
        center.clicked.connect(lambda: cu._center_plot_view(self))
        self._center = center
        return center
           
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
            with self.paused_stream() as dut:
                dut.antenna(int(antenna.currentText().split()[-1]))
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
            with self.paused_stream() as dut:
                dut.preselect_filter("On" in bpf.currentText())
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
            with self.paused_stream() as dut:
                dut.gain(g)
        gain.currentIndexChanged.connect(new_gain)
        return gain

    @inlineCallbacks
    def _read_update_ifgain_box(self):
        ifgain = yield self.dut.ifgain()
        self._ifgain_box.setValue(int(ifgain))

    def _ifgain_control(self):
        ifgain = QtGui.QSpinBox(self)
        ifgain.setRange(-10, 25)
        ifgain.setSuffix(" dB")
        self._ifgain_box = ifgain
        self._read_update_ifgain_box()
        def new_ifgain():
            with self.paused_stream() as dut:
                dut.ifgain(ifgain.value())
        ifgain.valueChanged.connect(new_ifgain)
        return ifgain

    @inlineCallbacks
    def _read_update_freq_edit(self):
        "Get current frequency from self.dut and update the edit box"
        self._update_freq_edit() # once immediately in case of long delay
        self.plot_state.center_freq = yield self.dut.freq()
        self._update_freq_edit()

    def _update_freq_edit(self):
        "Update the frequency edit box from self.plot_state.center_freq"
        if self.plot_state.center_freq is None:
            self._freq_edit.setText("---")
        else:
            self._freq_edit.setText("%0.1f" % (self.plot_state.center_freq / 1e6))

    def _freq_controls(self):
        cfreq = QtGui.QPushButton('  (2) Center Frequency')
        self._cfreq = cfreq
        cfreq.clicked.connect(lambda: cu._select_center_freq(self))
        
        
        freq = QtGui.QLineEdit("")
        self._freq_edit = freq
        self._read_update_freq_edit()
        def write_freq():
            try:
                f = float(freq.text())
            except ValueError:
                return
            if f < constants.MIN_FREQ:
                freq.setText(str(MIN_FREQ))
            elif f> constants.MAX_FREQ:
                freq.setText(str(MAX_FREQ))
            else:
                self.set_freq_mhz(f)
        freq.editingFinished.connect(write_freq)

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
                f = float(freq.text())
            except ValueError:
                self._update_freq_edit()
                return
            delta = float(steps.currentText().split()[1]) * factor
            freq.setText("%0.1f" % (f + delta))
            write_freq()
        freq_minus = QtGui.QPushButton('-')
        freq_minus.clicked.connect(lambda: freq_step(-1))
        self._freq_minus = freq_minus
        freq_plus = QtGui.QPushButton('+')
        freq_plus.clicked.connect(lambda: freq_step(1))
        self._freq_plus = freq_plus
        
        return cfreq, freq, steps, freq_plus, freq_minus
    
    def _fstart_controls(self):
        fstart = QtGui.QPushButton('(1) Start Frequency')
        self._fstart = fstart
        fstart.clicked.connect(lambda: cu._select_fstart(self))
        freq = QtGui.QLineEdit("")
        if self.plot_state.center_freq != None:
            freq.setText("%0.1f", (self.plot_state.center_freq/1e6))
        self._fstart_txt = freq
        return fstart, freq
        
    def _fstop_controls(self):
        fstop = QtGui.QPushButton('(3) Stop Frequency')
        self._fstop = fstop
        fstop.clicked.connect(lambda: cu._select_fstop(self))
        freq = QtGui.QLineEdit("")
        if self.plot_state.center_freq != None:
            freq.setText("%0.1f", (self.plot_state.center_freq/1e6))
        self._fstop_txt = freq
        return fstop, freq
    @inlineCallbacks
    def _read_update_span_rbw_boxes(self):
        self.decimation_factor = yield self.dut.decimation()
        self._span_box.setCurrentIndex(
            self._decimation_values.index(self.decimation_factor))
        self._update_rbw_box()

    def _update_rbw_box(self):
        d = self.decimation_factor
        for i, p in enumerate(self._points_values):
            r = constants.DEVICE_FULL_SPAN / d / p
            self._rbw_box.setItemText(i, "RBW: %s" % frequency_text(r))
            if self.plot_state.decimation_points and self.plot_state.decimation_points == d * p:
                self._rbw_box.setCurrentIndex(i)
        self.points = self._points_values[self._rbw_box.currentIndex()]

    def _span_rbw_controls(self):
        span = QtGui.QComboBox(self)
        decimation_values = [1] + [2 ** x for x in range(2, 10)]
        for d in decimation_values:
            span.addItem("Span: %s" % frequency_text(constants.DEVICE_FULL_SPAN / d))
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
            with self.paused_stream() as dut:
                dut.spp(self.points)
        rbw.setCurrentIndex(self._points_values.index(1024))
        rbw.currentIndexChanged.connect(new_rbw)

        return span, rbw

    def set_freq_mhz(self, f):
        # HOOK FSTART/FSTOP CHANGE HERE
        self.plot_state.center_freq = f * 1e6
        with self.paused_stream() as dut:
            dut.freq(self.plot_state.center_freq)
        
        # reset max hold whenever frequency is changed
        self.mhold_fft = None

    def set_decimation(self, d):
        self.decimation_factor = 1 if d == 0 else d
        with self.paused_stream() as dut:
            dut.decimation(d)
        
    def update_plot(self, pow_data, start_freq, stop_freq):
        if not self.plot_state.enable_plot:
            pow_data = self.plot_state._pow
        self._plot.window.setYRange(constants.PLOT_YMIN, constants.PLOT_YMAX)
        if start_freq != None and stop_freq != None:
            # update the frequency range (Hz)
            self.plot_state.freq_range = np.linspace(start_freq,stop_freq , len(pow_data))
       
        self.update_fft(pow_data)
        self.update_mhold(pow_data)
        self.update_marker(pow_data)
        self.update_delta(pow_data)
        
    def update_fft(self, pow_data):
            self._plot.fft_curve.setData(self.plot_state.freq_range,pow_data)

    def update_trig(self):
            freq_region = self._plot.freqtrig_lines.getRegion()
            self.trig_set = TriggerSettings(constants.LEVELED_TRIGGER_TYPE, 
                                                    min(freq_region), 
                                                    max(freq_region),
                                                    self._plot.amptrig_line.value() + 5) 
            self.dut.trigger(self.trig_set)
    
    def update_mhold(self, pow_data):
        if self.plot_state.mhold:
            if (self.plot_state.mhold_fft == None or len(self.plot_state.mhold_fft) != len(pow_data)):
                self.plot_state.mhold_fft = np.zeros(len(pow_data)) + constants.LNEG_NUM
                
            self.plot_state.mhold_fft = np.maximum(self.plot_state.mhold_fft,pow_data)
            self._plot.mhold_curve.setData(self.plot_state.freq_range,self.plot_state.mhold_fft)

    def update_marker(self, pow_data):
        if self.plot_state.marker:
            if self.plot_state.mhold:
                pow_data = self.plot_state.mhold_fft
                text_color = constants.ORANGE_NUM
            else:
                text_color = constants.TEAL_NUM
            if self.plot_state.marker_ind  == None:
                self.plot_state.marker_ind  = len(pow_data) / 2
            
            if self.plot_state.peak:
                self.plot_state.marker_ind  = find_max_index(pow_data)
                self.plot_state.peak = False

            elif self.plot_state.marker_ind  < 0:
                self.plot_state.marker_ind  = 0
                
            elif self.plot_state.marker_ind  >= len(pow_data):
                self.plot_state.marker_ind  = len(pow_data) - 1
           
            marker_freq = [self.plot_state.freq_range[self.plot_state.marker_ind ]]
            marker_power = [pow_data[self.plot_state.marker_ind]]
            marker_text = 'Frequency: %0.2f MHz \n Power %0.2f dBm' % (marker_freq[0]/1e6, marker_power[0])
            self._plot.marker_label.setText(text = marker_text, color = text_color)
            
            self._plot.marker_point.clear()
            self._plot.marker_point.addPoints(x = marker_freq, 
                                                    y = marker_power, 
                                                    symbol = '+', 
                                                    size = 20, pen = 'w', 
                                                    brush = 'w')
            
            
            window_freq = self._plot.view_box.viewRange()[0]
            labelx = window_freq[0] + 0.05*(window_freq[1] - window_freq[0])
            labely = constants.PLOT_YMAX + 5
            self._plot.marker_label.setPos(labelx, labely)
            
    def update_delta(self, pow_data):
        if self.plot_state.delta:
            if self.plot_state.mhold:
                pow_data = self.plot_state.mhold_fft      
                text_color = constants.ORANGE_NUM
            else:
                text_color = constants.TEAL_NUM
            
            if self.plot_state.delta_ind == None:
                self.plot_state.delta_ind = len(pow_data) / 2
            elif self.plot_state.delta_ind < 0:
                self.plot_state.delta_ind = 0
                
            elif self.plot_state.delta_ind >= len(pow_data):
                self.plot_state.delta_ind = len(pow_data) - 1
            
            delta_freq = [self.plot_state.freq_range[self.plot_state.delta_ind]]
            delta_power = [pow_data[self.plot_state.delta_ind]]
            delta_text = 'Frequency: %0.1f MHz \n Power %0.2f dBm' % (delta_freq[0]/1e6, delta_power[0])
            self._plot.delta_label.setText(text = delta_text, color = text_color)
           
            self._plot.delta_point.clear()
            self._plot.delta_point.addPoints(x =delta_freq, 
                                                    y = delta_power, 
                                                    symbol = '+', 
                                                    size = 20, pen = 'w', 
                                                    brush = 'w')
            
            window_freq = self._plot.view_box.viewRange()[0]
            labelx = (window_freq[0] + window_freq[1])/2 - 0.15*(window_freq[1] - window_freq[0])
            labely = constants.PLOT_YMAX + 5
            self._plot.delta_label.setPos(labelx, labely)            
            
            if self.plot_state.marker:
                freq_diff = np.abs((self.plot_state.freq_range[self.plot_state.delta_ind]/1e6) - (self.plot_state.freq_range[self.plot_state.marker_ind ]/1e6))
                power_diff = np.abs((pow_data[self.plot_state.delta_ind]) - (pow_data[self.plot_state.marker_ind ]))
                delta_text = 'Delta : %0.1f MHz \nDelta %0.2f dBm' % (freq_diff, power_diff )
                self._plot.diff_label.setText(text = delta_text, color = text_color)
                
                window_freq = self._plot.view_box.viewRange()[0]
                self._plot.diff_label.setPos((window_freq[0] + window_freq[1])/2 + 0.2*(window_freq[1] - window_freq[0]), 
                                                    constants.PLOT_YMAX + 5)
            else:
                self._plot.diff_label.setText(text= '')
    
    @contextmanager
    def paused_stream(self):
        yield self.dut

