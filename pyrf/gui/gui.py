
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
        hotKeyAction = QtGui.QAction('&Hotkey List', self)
        hotKeyAction.triggered.connect(self.open_hotkey_dialog)
        exitAction = QtGui.QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)
        helpMenu = menubar.addMenu('&Help')
        helpMenu.addAction(hotKeyAction)

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
    def open_hotkey_dialog(self):
        ok = QtGui.QMessageBox(self,'derpity derp', 'herp')
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
            if not self.plot_state.enable_plot:
                return
            # queue up the next capture while we update
            self.dut.capture(self.plot_state.points, 1)
            # compute FFT
            self.pow_data = compute_fft(self.dut, packet, self._vrt_context)          
            
            # grab center frequency/bandwidth to calculate axis width/height
            self.plot_state.center_freq = self._vrt_context['rffreq']
            self.plot_state.bandwidth = self._vrt_context['bandwidth']
            
            self.plot_state.start_freq = (self.plot_state.center_freq) - (self.plot_state.bandwidth / 2)
            self.plot_state.stop_freq = (self.plot_state.center_freq) + (self.plot_state.bandwidth / 2)
            if self._freq_edit.text() == '':
                self._update_freq_edit()
            self.update_plot()
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
                self.update_marker()
            
            elif self.plot_state.delta_sel:
                self.plot_state.delta_ind = find_nearest_index(click_freq, self.plot_state.freq_range)
                self.update_delta()
    
    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        grid.setColumnMinimumWidth(0, 600)
        grid.setColumnMinimumWidth(1, 600)
        grid.setColumnMinimumWidth(2, 600)

        # add plot widget
        grid.addWidget(self._plot.window,0,0,10,3)
                
        y = 0
        trig = self._trigger_control()
        grid.addWidget(trig, y, 3, 1, 1)
        mark = self._marker_control()
        grid.addWidget(mark, y, 4, 1, 1)
        delta = self._delta_control()
        grid.addWidget(delta, y, 5, 1, 1)
        mhold = self._mhold_control()
        grid.addWidget(mhold, y, 6, 1, 1)
        
        y += 1
        pause = self._pause_control()
        grid.addWidget(pause, y, 3, 1, 1)
        peak = self._peak_control()
        grid.addWidget(peak, y, 4, 1, 1)
        grid_en = self._grid_control()
        grid.addWidget(grid_en, y, 5, 1, 1)
        cu._grid_control(self)
        center = self._center_control()
        grid.addWidget(center, y, 6, 1, 1)

        y += 1
        grid.addWidget(self._antenna_control(), y, 3, 1, 2)
        grid.addWidget(self._bpf_control(), y, 5, 1, 2)
        
        y += 1
        grid.addWidget(self._gain_control(), y, 3, 1, 2)
        grid.addWidget(QtGui.QLabel('IF Gain:'), y, 5, 1, 1)
        grid.addWidget(self._ifgain_control(), y, 6, 1, 1)
        
        y += 1
        fstart_bt, fstart_txt = self._fstart_controls()
        grid.addWidget(fstart_bt, y, 3, 1, 1)
        grid.addWidget(fstart_txt, y, 4, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), y, 6, 1, 1)
        
        y += 1
        cfreq, freq, steps, freq_plus, freq_minus = self._freq_controls()
        grid.addWidget(cfreq, y, 3, 1, 1)
        grid.addWidget(freq, y, 4, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), y, 6, 1, 1)
        
        y += 1
        fstop_bt, fstop_txt = self._fstop_controls()
        grid.addWidget(fstop_bt, y, 3, 1, 1)
        grid.addWidget(fstop_txt, y, 4, 1, 2)
        grid.addWidget(QtGui.QLabel('MHz'), y, 6, 1, 1)
        
        # select center freq
        gui_config.select_center(self)
        y += 1
        grid.addWidget(freq_minus, y, 3, 1, 1)
        grid.addWidget(steps, y, 4, 1, 2)
        grid.addWidget(freq_plus, y, 6, 1, 1)
        
        y += 1
        span, rbw = self._span_rbw_controls()
        grid.addWidget(span, y, 3, 1, 2)
        grid.addWidget(rbw, y, 5, 1, 2)
        
        marker_label, delta_label, diff_label = self._marker_labels()
        grid.addWidget(marker_label, 0, 0,1, 1)
        grid.addWidget(delta_label, 0, 1,1, 1)
        grid.addWidget(diff_label , 0, 2,1, 1)
        
        self.setLayout(grid)
        self.show()
    
    def _trigger_control(self):
        trigger = QtGui.QPushButton('Trigger', self)
        trigger.setToolTip("<span style=\"color:black;\">[T]<br>Turn the Triggers on/off</span>") 
        trigger.clicked.connect(lambda: cu._trigger_control(self))
        self._trigger = trigger
        return trigger
    
    def _marker_control(self):
        marker = QtGui.QPushButton('Marker 1', self)
        marker.setToolTip("<span style=\"color:black;\">[M]<br>Turn Marker 1 on/off</span>") 
        marker.clicked.connect(lambda: cu._marker_control(self))
        self._marker = marker
        return marker
        
    def _delta_control(self):
        delta = QtGui.QPushButton('Marker 2', self)
        delta.setToolTip("<span style=\"color:black;\">[K]<br>Turn Marker 2 on/off</span>") 
        delta.clicked.connect(lambda: cu._delta_control(self))
        self._delta = delta
        return delta
    
    def _peak_control(self):
        peak = QtGui.QPushButton('Peak', self)
        peak.setToolTip("<span style=\"color:black;\">[P]<br>Find peak of the selected spectrum</span>") 
        peak.clicked.connect(lambda: cu._find_peak(self))
        self._peak = peak
        return peak
        
    def _mhold_control(self):
        mhold = QtGui.QPushButton('Max Hold', self)
        mhold.setToolTip("<span style=\"color:black;\">[H]<br>Turn the Max Hold on/off</span>") 
        mhold.clicked.connect(lambda: cu._mhold_control(self))
        self._mhold = mhold
        return mhold
        
    def _grid_control(self):
        plot_grid = QtGui.QPushButton('Grid', self)
        plot_grid.setToolTip("<span style=\"color:black;\">[G]<br>Turn the Grid on/off</span>") 
        plot_grid.clicked.connect(lambda: cu._grid_control(self))
        self._grid = plot_grid
        return plot_grid

    def _center_control(self):
        center = QtGui.QPushButton('Center View', self)
        center.setToolTip("<span style=\"color:black;\">[C]<br>Center the Plot View around the available spectrum</span>") 
        center.clicked.connect(lambda: cu._center_plot_view(self))
        self._center = center
        return center
        
    def _pause_control(self):
        pause = QtGui.QPushButton('Pause', self)
        pause.setToolTip("<span style=\"color:black;\">[Space Bar]<br>Pause the plot window</span>") 
        pause.clicked.connect(lambda: cu._enable_plot(self))
        self._pause = pause
        return pause
           
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

        self._freq_edit.setText("%0.1f" % (self.plot_state.center_freq / 1e6))
        self._fstart_edit.setText("%0.1f" % (self.plot_state.start_freq/ 1e6))
        self._fstop_edit.setText("%0.1f" % (self.plot_state.stop_freq/ 1e6))
    
    def _freq_controls(self):
        cfreq = QtGui.QPushButton('Center Frequency')
        cfreq.setToolTip("<span style=\"color:black;\">[2]<br>Tune the center frequency</span>") 

        self._cfreq = cfreq
        cfreq.clicked.connect(lambda: cu._select_center_freq(self))

        freq = QtGui.QLineEdit("")
        self._freq_edit = freq
        def write_freq():
            try:
                f = float(freq.text())
            except ValueError:
                return
            if f < constants.MIN_FREQ:
                freq.setText(str(constants.MIN_FREQ))
            elif f> constants.MAX_FREQ:
                freq.setText(str(constants.MAX_FREQ))
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
        fstart = QtGui.QPushButton('Start Frequency')
        fstart.setToolTip("<span style=\"color:black;\">[1]<br>Tune the start frequency</span>")
        self._fstart = fstart
        fstart.clicked.connect(lambda: cu._select_fstart(self))
        freq = QtGui.QLineEdit("")
        if self.plot_state.center_freq != None:
            freq.setText("%0.1f", (self.plot_state.center_freq/1e6))
        self._fstart_edit = freq
        return fstart, freq
        
    def _fstop_controls(self):
        fstop = QtGui.QPushButton('Stop Frequency')
        fstop.setToolTip("<span style=\"color:black;\">[3]<br>Tune the stop frequency</span>") 
        self._fstop = fstop
        fstop.clicked.connect(lambda: cu._select_fstop(self))
        freq = QtGui.QLineEdit("")
        if self.plot_state.center_freq != None:
            freq.setText("%0.1f", (self.plot_state.center_freq/1e6))
        self._fstop_edit = freq
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
            self.plot_state.reset_freq_bounds()
            
        span.currentIndexChanged.connect(new_span)

        rbw = QtGui.QComboBox(self)
        self._points_values = [2 ** x for x in range(8, 16)]
        self._rbw_box = rbw
        rbw.addItems([str(p) for p in self._points_values])
        self._read_update_span_rbw_boxes()

        def new_rbw():
            self.plot_state.points = self._points_values[rbw.currentIndex()]
            self.decimation_points = self.decimation_factor * self.plot_state.points
            with self.paused_stream() as dut:
                dut.spp(self.plot_state.points)
        rbw.setCurrentIndex(self._points_values.index(1024))
        rbw.currentIndexChanged.connect(new_rbw)
        return span, rbw

    def set_freq_mhz(self, f):
        # TODO: HOOK FSTART/FSTOP CHANGE HERE
        if self.plot_state.freq_sel == 'CENT':
            self.plot_state.center_freq = f * 1e6
            
            # reset max hold whenever frequency is changed
            self.plot_state.mhold_fft = None
            
            with self.paused_stream() as dut:
                dut.freq(self.plot_state.center_freq)
        self.plot_state.update_freq(self.plot_state.freq_sel)
        self._update_freq_edit()
            

    def set_decimation(self, d):
        self.decimation_factor = 1 if d == 0 else d
        with self.paused_stream() as dut:
            dut.decimation(d)
    def _marker_labels(self):
        marker_label = QtGui.QLabel('')
        marker_label.setAlignment(4)
        marker_label.setStyleSheet('color: %s;' % constants.TEAL)
        marker_label.setMinimumHeight(25)
        self._marker_lab = marker_label
        
        delta_label = QtGui.QLabel('')
        delta_label.setAlignment(4)
        delta_label.setStyleSheet('color: %s;' % constants.TEAL)
        delta_label.setMinimumHeight(25)
        self._delta_lab = delta_label
        
        diff_label = QtGui.QLabel('')
        diff_label.setAlignment(4)
        diff_label.setStyleSheet('color: %s;' % constants.TEAL)
        diff_label.setMinimumHeight(25)
        self._diff_lab = diff_label
        return marker_label,delta_label, diff_label
        
    def update_plot(self):      
        self._plot.window.setYRange(constants.PLOT_YMIN, constants.PLOT_YMAX)
        self.plot_state.update_freq_range(self.plot_state.start_freq,
                                                self.plot_state.stop_freq , 
                                                len(self.pow_data))
       
        self.update_fft()
        self.update_mhold()
        self.update_marker()
        self.update_delta()
        
    def update_fft(self):
            self._plot.fft_curve.setData(self.plot_state.freq_range,self.pow_data)

    def update_trig(self):
            freq_region = self._plot.freqtrig_lines.getRegion()
            self.trig_set = TriggerSettings(constants.LEVELED_TRIGGER_TYPE, 
                                                    min(freq_region), 
                                                    max(freq_region),
                                                    self._plot.amptrig_line.value()) 
            self.dut.trigger(self.trig_set)
    
    def update_mhold(self):
        if self.plot_state.mhold:
            if (self.plot_state.mhold_fft == None or len(self.plot_state.mhold_fft) != len(self.pow_data)):
                self.plot_state.mhold_fft = np.zeros(len(self.pow_data)) + constants.LNEG_NUM
                
            self.plot_state.mhold_fft = np.maximum(self.plot_state.mhold_fft,self.pow_data)
            self._plot.mhold_curve.setData(self.plot_state.freq_range,self.plot_state.mhold_fft)

    def update_marker(self):
        if self.plot_state.marker:
            if self.plot_state.mhold:
                pow_ = self.plot_state.mhold_fft
                self._marker_lab.setStyleSheet('color: %s;' % constants.ORANGE)
            else:
                pow_ = self.pow_data
                self._marker_lab.setStyleSheet('color: %s;' % constants.TEAL)
            if self.plot_state.marker_ind  == None:
                self.plot_state.marker_ind  = len(pow_) / 2

            elif self.plot_state.marker_ind  < 0:
                self.plot_state.marker_ind  = 0
                
            elif self.plot_state.marker_ind  >= len(pow_):
                self.plot_state.marker_ind  = len(pow_) - 1
           
            marker_freq = [self.plot_state.freq_range[self.plot_state.marker_ind ]]
            markerpause_ffter = [pow_[self.plot_state.marker_ind]]
            marker_text = 'Frequency: %0.2f MHz \n Power %0.2f dBm' % (marker_freq[0]/1e6, markerpause_ffter[0])
            self._marker_lab.setText(marker_text)
            
            self._plot.marker_point.clear()
            self._plot.marker_point.addPoints(x = marker_freq, 
                                                    y = markerpause_ffter, 
                                                    symbol = '+', 
                                                    size = 20, pen = 'w', 
                                                    brush = 'w')

    def update_delta(self):
        if self.plot_state.delta:
            if self.plot_state.mhold:
                pow_ = self.plot_state.mhold_fft
                self._diff_lab.setStyleSheet('color: %s;' % constants.ORANGE)
                self._delta_lab.setStyleSheet('color: %s;' % constants.ORANGE)
            else:
                pow_ = self.pow_data
                self._diff_lab.setStyleSheet('color: %s;' % constants.TEAL)
                self._delta_lab.setStyleSheet('color: %s;' % constants.TEAL)           
            
            if self.plot_state.delta_ind == None:
                self.plot_state.delta_ind = len(pow_) / 2
            elif self.plot_state.delta_ind < 0:
                self.plot_state.delta_ind = 0
                
            elif self.plot_state.delta_ind >= len(pow_):
                self.plot_state.delta_ind = len(pow_) - 1
            
            delta_freq = [self.plot_state.freq_range[self.plot_state.delta_ind]]
            delta_power = [pow_[self.plot_state.delta_ind]]
            delta_text = 'Frequency: %0.1f MHz \n Power %0.2f dBm' % (delta_freq[0]/1e6, delta_power[0])
            self._delta_lab.setText(delta_text)
           
            self._plot.delta_point.clear()
            self._plot.delta_point.addPoints(x =delta_freq, 
                                                    y = delta_power, 
                                                    symbol = '+', 
                                                    size = 20, pen = 'w', 
                                                    brush = 'w')

            if self.plot_state.marker:
                freq_diff = np.abs((self.plot_state.freq_range[self.plot_state.delta_ind]/1e6) - (self.plot_state.freq_range[self.plot_state.marker_ind ]/1e6))
                power_diff = np.abs((pow_[self.plot_state.delta_ind]) - (pow_[self.plot_state.marker_ind ]))
                delta_text = 'Delta : %0.1f MHz \nDelta %0.2f dBm' % (freq_diff, power_diff )
                self._diff_lab.setText(delta_text)
            else:
                self._diff_lab.setText('')

    
    @contextmanager
    def paused_stream(self):
        yield self.dut

