
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
import time
from contextlib import contextmanager
from util import find_max_index, find_nearest_index
from util import hotkey_util
import constants
import control_util as cu
from plot_widget import plot
import gui_config
from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.config import TriggerSettings
from pyrf.capture_device import CaptureDevice

try:
    from twisted.internet.defer import inlineCallbacks
except ImportError:
    def inlineCallbacks(fn):
        pass

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 400

class MainWindow(QtGui.QMainWindow):
    """
    The main window and menus
    """
    def __init__(self, name=None):
        super(MainWindow, self).__init__()
        self.resize(WINDOW_WIDTH,WINDOW_HEIGHT)
        self.initUI()


        self.show()
    
    def initUI(self):
        name = None
        if len(sys.argv) > 1:
            name = sys.argv[1]
        self.mainPanel = MainPanel()
        openAction = QtGui.QAction('&Open Device', self)
        openAction.triggered.connect( self.mainPanel.open_device_dialog)
        exitAction = QtGui.QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.triggered.connect(self.close)
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openAction)
        fileMenu.addAction(exitAction)
        self.setWindowTitle('Spectrum Analyzer')
        self.setCentralWidget(self.mainPanel)
        self.mainPanel.show()
        if name:
            self.mainPanel.open_device(name)
        else:
            self.mainPanel.open_device_dialog()
    
    def closeEvent(self, event):
        if self.mainPanel.dut:
            self.mainPanel.dut.abort()
            self.mainPanel.dut.flush()
            self.mainPanel.dut.reset()
        event.accept()
        self.mainPanel._reactor.stop()


class MainPanel(QtGui.QWidget):
    """
    The spectrum view and controls
    """
    def __init__(self):
        self.dut = None
        self.control_widgets = []
        super(MainPanel, self).__init__()
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.resize(WINDOW_WIDTH,WINDOW_HEIGHT)
        self.plot_state = gui_config.plot_state()
        # plot window
        self._plot = plot(self)
        self._vrt_context = {}
        self.initUI()
        self.disable_controls()
        self._reactor = self._get_reactor()

    def _get_reactor(self):
        # late import because installReactor is being used
        from twisted.internet import reactor
        return reactor

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
        dut = WSA(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)
        self.dut = dut
        if dut.properties.model == 'WSA5000':
            self._antenna_box.hide()
            self._gain_box.hide()
            self._trigger.hide()
            #self._attenuator_box.show()
        else:
            self._antenna_box.show()
            self._gain_box.show()
            self._trigger.show()
            #self._attenuator_box.hide()

        self.sweep_dut = SweepDevice(dut, self.receive_data)
        self.cap_dut = CaptureDevice(dut, self.receive_data)
        self.enable_controls()
        cu._select_fstart(self)
        self.read_sweep()

    def read_sweep(self):
        #TODO: find cleaner way to do this
        self.plot_state.dev_set.pop('freq', None)
        self.plot_state.dev_set.pop('trigger', None)
        self.sweep_dut.capture_power_spectrum(self.plot_state.fstart,
                                              self.plot_state.fstop,
                                              self.plot_state.rbw,
                                              self.plot_state.dev_set,
                                              continuous = False)

    def read_trigg(self):
        device_set = self.plot_state.dev_set
        #TODO: find cleaner way to do this
        device_set['freq'] = self.plot_state.center_freq
        device_set['trigger'] = self.plot_state.trig_set

        self.cap_dut.capture_power_spectrum(device_set,self.plot_state.rbw)


    def receive_data(self, fstart, fstop, pow_):
        if not self.plot_state.enable_plot:
            return
        if self.plot_state.trig_set:
            self.read_trigg()
        else:
            self.read_sweep()
        self.pow_data = pow_
        self.update_plot()


    def keyPressEvent(self, event):
        if self.dut:
            hotkey_util(self, event)
           
    def mousePressEvent(self, event):
        if self.dut:
            if event.button() == QtCore.Qt.MouseButton.LeftButton:
                click_pos =  event.pos().x() - 68
                plot_window_width = self._plot.window.width() - 68

                if click_pos < plot_window_width and click_pos > 0:

                    window_freq = self._plot.view_box.viewRange()[0]
                    window_bw =  (window_freq[1] - window_freq[0])
                    click_freq = ((float(click_pos) / float(plot_window_width)) * float(window_bw)) + window_freq[0]

                    if self.plot_state.marker_sel:
                        self._marker.setDown(True)
                        self.plot_state.marker_ind  = find_nearest_index(click_freq, self.plot_state.freq_range)
                        self.update_marker()
                    
                    elif self.plot_state.delta_sel:
                        self._delta.setDown(True)
                        self.plot_state.delta_ind = find_nearest_index(click_freq, self.plot_state.freq_range)
                        self.update_delta()
                    self.update_diff()
    def initUI(self):
        grid = QtGui.QGridLayout()
        grid.setSpacing(10)
        for x in range(8):
            grid.setColumnMinimumWidth(x, 300)
        grid.setRowMinimumHeight(14, 800)

        # add plot widget
        plot_width = 8
        grid.addWidget(self._plot.window,0,0,15,plot_width)

        marker_label, delta_label, diff_label = self._marker_labels()
        grid.addWidget(marker_label, 0, 1, 1, 2)
        grid.addWidget(delta_label, 0, 3, 1, 2)
        grid.addWidget(diff_label , 0, 5, 1, 2)
 
        y = 0
        x = plot_width
        grid.addWidget(self._device_controls(), y, x, 2, 5)
        y += 2
        grid.addWidget(self._freq_controls(), y, x, 4, 5)
        y += 4
        grid.addWidget(self._plot_controls(), y, x, 4, 5)

        self.update_freq()
        self.setLayout(grid)

        
    
    def _device_controls(self):
        dev_group = QtGui.QGroupBox("Device Control")
        self.dev_group = dev_group
        
        dev_layout = QtGui.QVBoxLayout()
        
        first_row = QtGui.QHBoxLayout()
        first_row.addWidget(self._antenna_control())
        first_row.addWidget(self._trigger_control())
        first_row.addWidget(self._attenuator_control())
        
        second_row = QtGui.QHBoxLayout()
        second_row.addWidget(self._gain_control())
        second_row.addWidget(self._ifgain_control())
        
        dev_layout.addLayout(first_row)
        dev_layout.addLayout(second_row)

        dev_group.setLayout(dev_layout)         
        return dev_group
    def _antenna_control(self):
        antenna = QtGui.QComboBox(self)
        antenna.setToolTip("Choose Antenna") 
        antenna.addItem("Antenna 1")
        antenna.addItem("Antenna 2")
        self._antenna_box = antenna
        self.control_widgets.append(self._antenna_box)
        def new_antenna():
            self.plot_state.dev_set['antenna'] = (int(antenna.currentText().split()[-1]))
        
        antenna.currentIndexChanged.connect(new_antenna)
        return antenna

    def _gain_control(self):
        gain = QtGui.QComboBox(self)
        gain.setToolTip("Choose RF Gain setting") 
        gain_values = ['VLow', 'Low', 'Med', 'High']
        for g in gain_values:
            gain.addItem("RF Gain: %s" % g)
        self._gain_values = [g.lower() for g in gain_values]
        self._gain_box = gain
        self.control_widgets.append(self._gain_box)
        def new_gain():
            self.plot_state.dev_set['gain'] = gain.currentText().split()[-1].lower().encode('ascii')
        gain.currentIndexChanged.connect(new_gain)
        return gain

    def _ifgain_control(self):
        ifgain = QtGui.QSpinBox(self)
        ifgain.setToolTip("Choose IF Gain setting")
        ifgain.setRange(-10, 25)
        ifgain.setSuffix(" dB")
        self._ifgain_box = ifgain
        self.control_widgets.append(self._ifgain_box)
        def new_ifgain():
            self.plot_state.dev_set['ifgain'] = ifgain.value()
        ifgain.valueChanged.connect(new_ifgain)
        return ifgain
    
    def _trigger_control(self):
        trigger = QtGui.QCheckBox("Trigger")
        trigger.setToolTip("[T]\nTurn the Triggers on/off") 
        trigger.clicked.connect(lambda: cu._trigger_control(self))
        self._trigger = trigger
        self.control_widgets.append(self._trigger)
        return trigger

    def _attenuator_control(self):
        attenuator = QtGui.QCheckBox("Attenuator")
        attenuator.setChecked(True)
        def new_attenuator():
            self.plot_state.dev_set['attenuator'] = attenuator.isChecked()
        attenuator.clicked.connect(new_attenuator)
        self._attenuator_box = attenuator
        self.control_widgets.append(attenuator)
        return attenuator
    
    def _freq_controls(self):
        freq_group = QtGui.QGroupBox("Frequency Control")
        self._freq_group = freq_group
        
        freq_layout = QtGui.QVBoxLayout()
        
        fstart_hbox = QtGui.QHBoxLayout()
        fstart_bt, fstart_txt = self._fstart_controls()
        fstart_hbox.addWidget(fstart_bt)
        fstart_hbox.addWidget(fstart_txt)
        fstart_hbox.addWidget(QtGui.QLabel('MHz'))
        
        cfreq_hbox = QtGui.QHBoxLayout()
        cfreq_bt, cfreq_txt = self._center_freq()
        cfreq_hbox.addWidget(cfreq_bt)
        cfreq_hbox.addWidget(cfreq_txt)
        cfreq_hbox.addWidget(QtGui.QLabel('MHz'))
        
        bw_hbox = QtGui.QHBoxLayout()
        bw_bt, bw_txt = self._bw_controls()
        bw_hbox.addWidget(bw_bt)
        bw_hbox.addWidget(bw_txt)
        bw_hbox.addWidget(QtGui.QLabel('MHz'))
        
        fstop_hbox = QtGui.QHBoxLayout()
        fstop_bt, fstop_txt = self._fstop_controls()
        fstop_hbox.addWidget(fstop_bt)
        fstop_hbox.addWidget(fstop_txt)
        fstop_hbox.addWidget(QtGui.QLabel('MHz'))
        
        freq_inc_hbox = QtGui.QHBoxLayout()
        freq_inc_steps, freq_inc_minus, freq_inc_plus = self._freq_incr()
        freq_inc_hbox.addWidget(freq_inc_minus)
        freq_inc_hbox.addWidget(freq_inc_steps)
        freq_inc_hbox.addWidget(freq_inc_plus)
        
        rbw_hbox = QtGui.QHBoxLayout()
        rbw = self._rbw_controls()
        rbw_hbox.addWidget(QtGui.QLabel('Resolution Bandwidth:'))
        rbw_hbox.addWidget(rbw)
        
        freq_layout.addLayout(fstart_hbox)
        freq_layout.addLayout(cfreq_hbox)
        freq_layout.addLayout(bw_hbox)
        freq_layout.addLayout(fstop_hbox)
        freq_layout.addLayout(freq_inc_hbox)
        freq_layout.addLayout(rbw_hbox)
        freq_group.setLayout(freq_layout)
        
        return freq_group
    def _center_freq(self):
        cfreq = QtGui.QPushButton('Center')
        cfreq.setToolTip("[2]\nTune the center frequency") 
        self._cfreq = cfreq
        cfreq.clicked.connect(lambda: cu._select_center_freq(self))
        freq_edit = QtGui.QLineEdit(str(self.plot_state.center_freq/constants.MHZ))
        self._freq_edit = freq_edit
        self.control_widgets.append(self._cfreq)
        self.control_widgets.append(self._freq_edit)
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
        self.control_widgets.append(self._freq_plus)
        self.control_widgets.append(self._freq_minus)
        self.control_widgets.append(self._fstep_box)
        return  steps, freq_plus, freq_minus
    
    
    def _bw_controls(self):
        bw = QtGui.QPushButton('Span')
        bw.setToolTip("[3]\nChange the bandwidth of the current plot")
        self._bw = bw
        bw.clicked.connect(lambda: cu._select_bw(self))
        bw_edit = QtGui.QLineEdit(str(self.plot_state.bandwidth/constants.MHZ))
        def freq_change():
            cu._select_bw(self)
            self.update_freq()
            self.update_freq_edit()   
        bw_edit.returnPressed.connect(lambda: freq_change())
        self._bw_edit = bw_edit
        self.control_widgets.append(self._bw_edit)
        self.control_widgets.append(self._bw)
        return bw, bw_edit
    
    def _fstart_controls(self):
        fstart = QtGui.QPushButton('Start')
        fstart.setToolTip("[1]\nTune the start frequency")
        self._fstart = fstart
        fstart.clicked.connect(lambda: cu._select_fstart(self))
        freq = QtGui.QLineEdit(str(self.plot_state.fstart/constants.MHZ))
        def freq_change():
            cu._select_fstart(self)
            self.update_freq()
            self.update_freq_edit()
            
        freq.returnPressed.connect(lambda: freq_change())
        self._fstart_edit = freq
        self.control_widgets.append(self._fstart)
        self.control_widgets.append(self._fstart_edit)
        return fstart, freq
        
    def _fstop_controls(self):
        fstop = QtGui.QPushButton('Stop')
        fstop.setToolTip("[4]Tune the stop frequency") 
        self._fstop = fstop
        fstop.clicked.connect(lambda: cu._select_fstop(self))
        freq = QtGui.QLineEdit(str(self.plot_state.fstop/constants.MHZ))
        def freq_change():
            cu._select_fstop(self)   
            self.update_freq()
            self.update_freq_edit()            
        freq.returnPressed.connect(lambda: freq_change())
        self._fstop_edit = freq
        self.control_widgets.append(self._fstop)
        self.control_widgets.append(self._fstop_edit)
        return fstop, freq
           
    def _rbw_controls(self):
        rbw = QtGui.QComboBox(self)
        rbw.setToolTip("Change the RBW of the FFT plot")
        self._points_values = constants.RBW_VALUES
        self._rbw_box = rbw
        rbw.addItems([str(p) + ' KHz' for p in self._points_values])
        def new_rbw():
            self.plot_state.update_freq_set(rbw = self._points_values[rbw.currentIndex()])
        rbw.setCurrentIndex(0)
        rbw.currentIndexChanged.connect(new_rbw)
        self.control_widgets.append(self._rbw_box)
        return rbw

    def update_freq(self, delta = None):
            
        if delta == None:
            delta = 0                
        if self.plot_state.freq_sel == 'CENT':
            try:
                f = (float(self._freq_edit.text()) + delta) * constants.MHZ
            except ValueError:
                return
            if f > constants.MAX_FREQ or f < constants.MIN_FREQ:
                return
            self.plot_state.update_freq_set(fcenter = f)

        elif self.plot_state.freq_sel == 'FSTART':
            try:
                f = (float(self._fstart_edit.text()) + delta) * constants.MHZ 
            except ValueError:
                return
            if f > (constants.MAX_FREQ) or f < (constants.MIN_FREQ) or f > self.plot_state.fstop:
                return
            self.plot_state.update_freq_set(fstart = f)
            
        elif self.plot_state.freq_sel == 'FSTOP': 
            try:
                f = (float(self._fstop_edit.text()) + delta) * constants.MHZ 
            except ValueError:
                return
            if f > constants.MAX_FREQ or f < constants.MIN_FREQ or f < self.plot_state.fstart:
                return
            self.plot_state.update_freq_set(fstop = f)
        
        elif self.plot_state.freq_sel == 'BW':
            try:
                f = (float(self._bw_edit.text()) + delta) * constants.MHZ
            except ValueError:
                return
            if f < 0:
                return
            self.plot_state.update_freq_set(bw = f)
    
    def update_freq_edit(self):
        self._fstop_edit.setText("%0.1f" % (self.plot_state.fstop/ 1e6))
        self._fstart_edit.setText("%0.1f" % (self.plot_state.fstart/ 1e6))
        self._freq_edit.setText("%0.1f" % (self.plot_state.center_freq / 1e6))
        self._bw_edit.setText("%0.1f" % (self.plot_state.bandwidth / 1e6))
    
    def _plot_controls(self):

        plot_group = QtGui.QGroupBox("Plot Control")
        self._plot_group = plot_group
        
        plot_controls_layout = QtGui.QVBoxLayout()
        
        first_row = QtGui.QHBoxLayout()
        first_row.addWidget(self._marker_control())
        first_row.addWidget(self._delta_control())
        
        second_row = QtGui.QHBoxLayout()
        second_row.addWidget(self._peak_control())
        second_row.addWidget(self._mhold_control())
        
        third_row = QtGui.QHBoxLayout()
        third_row.addWidget(self._pause_control())
        third_row.addWidget(self._center_control())
        
        plot_controls_layout.addLayout(first_row)
        plot_controls_layout.addLayout(second_row)
        plot_controls_layout.addLayout(third_row)
        
        plot_group.setLayout(plot_controls_layout)
        
        return plot_group
    def _marker_control(self):
        marker = QtGui.QCheckBox('Marker 1')
        marker.setToolTip("[M]\nTurn Marker 1 on/off") 
        marker.clicked.connect(lambda: cu._marker_control(self))
        self._marker = marker
        self.control_widgets.append(self._marker)
        return marker
        
    def _delta_control(self):
        delta = QtGui.QCheckBox('Marker 2')
        delta.setToolTip("[K]\nTurn Marker 2 on/off") 
        delta.clicked.connect(lambda: cu._delta_control(self))
        self._delta = delta
        self.control_widgets.append(self._delta)
        return delta
    
    def _peak_control(self):
        peak = QtGui.QPushButton('Peak')
        peak.setToolTip("[P]\nFind peak of the selected spectrum") 
        peak.clicked.connect(lambda: cu._find_peak(self))
        self._peak = peak
        self.control_widgets.append(self._peak)
        return peak
        
    def _mhold_control(self):
        mhold = QtGui.QPushButton('Max Hold')
        mhold.setToolTip("[H]\nTurn the Max Hold on/off") 
        mhold.clicked.connect(lambda: cu._mhold_control(self))
        self._mhold = mhold
        self.control_widgets.append(self._mhold)
        return mhold
        
    def _center_control(self):
        center = QtGui.QPushButton('Recenter')
        center.setToolTip("[C]\nCenter the Plot View around the available spectrum") 
        center.clicked.connect(lambda: cu._center_plot_view(self))
        self._center_bt = center
        self.control_widgets.append(self._center_bt)
        return center
        
    def _pause_control(self):
        pause = QtGui.QPushButton('Pause')
        pause.setToolTip("[Space Bar]\n pause the plot window") 
        pause.clicked.connect(lambda: cu._enable_plot(self))
        self._pause = pause
        self.control_widgets.append(self._pause)
        return pause
    def _marker_labels(self):
        marker_label = QtGui.QLabel('')
        marker_label.setStyleSheet('color: %s;' % constants.TEAL)
        marker_label.setMinimumHeight(25)
        self._marker_lab = marker_label
        
        delta_label = QtGui.QLabel('')
        delta_label.setStyleSheet('color: %s;' % constants.TEAL)
        delta_label.setMinimumHeight(25)
        self._delta_lab = delta_label
        
        diff_label = QtGui.QLabel('')
        diff_label.setStyleSheet('color: %s;' % constants.TEAL)
        diff_label.setMinimumHeight(25)
        self._diff_lab = diff_label
        return marker_label,delta_label, diff_label
        
    def update_plot(self):
       
        self.plot_state.update_freq_range(self.plot_state.fstart,
                                              self.plot_state.fstop , 
                                              len(self.pow_data))

        self.update_fft()
        self.update_marker()
        self.update_delta()
        self.update_diff()
        
    def update_fft(self):

        if self.plot_state.mhold:
            if (self.plot_state.mhold_fft == None or len(self.plot_state.mhold_fft) != len(self.pow_data)):
                self.plot_state.mhold_fft = self.pow_data
            
            self.plot_state.mhold_fft = np.maximum(self.plot_state.mhold_fft,self.pow_data)
            self._plot.fft_curve.setData(x = self.plot_state.freq_range,
                                            y = self.plot_state.mhold_fft, 
                                            pen = constants.ORANGE_NUM)
        else:
            self._plot.fft_curve.setData(x = self.plot_state.freq_range, 
                                            y = self.pow_data, 
                                            pen = constants.TEAL_NUM)

    def update_trig(self):
            freq_region = self._plot.freqtrig_lines.getRegion()
            self.plot_state.trig_set = TriggerSettings(constants.LEVELED_TRIGGER_TYPE, 
                                                    min(freq_region), 
                                                    max(freq_region),
                                                    self._plot.amptrig_line.value())
            if self.plot_state.trig_set:
                self.dut.trigger(self.plot_state.trig_set)
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
                self._delta_lab.setStyleSheet('color: %s;' % constants.ORANGE)
            else:
                pow_ = self.pow_data
                self._delta_lab.setStyleSheet('color: %s;' % constants.TEAL)           
            
            if self.plot_state.delta_ind == None:
                self.plot_state.delta_ind = (len(pow_) / 2)
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

    def update_diff(self):
        if self.plot_state.mhold:
            pow_ = self.plot_state.mhold_fft
            self._diff_lab.setStyleSheet('color: %s;' % constants.ORANGE)
        else:
            pow_ = self.pow_data
            self._diff_lab.setStyleSheet('color: %s;' % constants.TEAL)  
            
        if self.plot_state.marker and self.plot_state.delta:
            freq_diff = np.abs((self.plot_state.freq_range[self.plot_state.delta_ind]/1e6) - (self.plot_state.freq_range[self.plot_state.marker_ind ]/1e6))
            power_diff = np.abs((pow_[self.plot_state.delta_ind]) - (pow_[self.plot_state.marker_ind ]))
            delta_text = 'Delta : %0.1f MHz \nDelta %0.2f dBm' % (freq_diff, power_diff )
            self._diff_lab.setText(delta_text)
        else:
            self._diff_lab.setText('')

    def enable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(True)
        
    def disable_controls(self):
        for item in self.control_widgets:
            item.setEnabled(False)

        
