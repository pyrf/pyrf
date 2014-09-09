#!/usr/bin/env python

import sys
import random

from PySide import QtGui, QtCore
import pyqtgraph as pg
import numpy as np
import pyrf
from pyrf.gui.persistence_plot_widget import PersistencePlotWidget

from pyrf.devices.thinkrf import WSA
from pyrf.util import read_data_and_context
from pyrf.numpy_util import compute_fft
from pyrf.gui.waterfall_widget import WaterfallModel

class MainWin(QtGui.QMainWindow):
    def __init__(self):
        
        super(MainWin, self).__init__()
        self.resize(900, 500)
        
        self._using_mock_wsa = False
        
        self.InitWSA()
        self.DoCreateWidgets()
        self.DoLayout()
        self.DoHandlers()
        
        self.StartDataCollection()
    
    def InitWSA(self):
        if len(sys.argv) > 1:
            self.wsa = MyWifiWSA(sys.argv[1])
        else:
            self.wsa = MockWSA("foo")
            self._using_mock_wsa = True
        
    def StartDataCollection(self):
        self._capture_period_s = 0.025
        self.wsa.start_continuous_capture(self._capture_period_s)
    
    def DoCreateWidgets(self):
        global data_model
        self._main_wid = QtGui.QWidget()
        data_model = self.wsa.capture_history
        self._plt = PersistencePlotWidget(self, data_model=data_model)
        self._plt.setXRange(self.wsa._start_MHz, self.wsa._stop_MHz, padding=0)
        
        self._plt.showGrid(True, True)
        
        if self._using_mock_wsa:
            self._plt.setYRange(-50, 0)
        else:
            self._plt.setYRange(-120, -40)
        
        self._gradient_editor = self._plt.gradient_editor
    
    def DoLayout(self):
        layout = QtGui.QHBoxLayout(self._main_wid)
        layout.addWidget(self._gradient_editor)
        layout.addWidget(self._plt)
        self.setCentralWidget(self._main_wid)
    
    def DoHandlers(self):
        pass

def calc_vrt_sample_time_s(vrt_data):
    return vrt_data.tsi + vrt_data.tsf * 1e-12

class MyWifiWSA(object):
    """A cheap/simple/incomplete WSA instrument abstraction.
    
    Hides driver internals that people using the device as a spectrum
    analyzer may not care about.
    
    """
    def __init__(self, ip_address):
        super(MyWifiWSA, self).__init__()
        self._init_hardware(ip_address)
        
        self._numpts = 4096
        self._center_MHz = 2447.
        self._span_MHz = 125.
        self._start_MHz = self._center_MHz - (self._span_MHz / 2)
        self._stop_MHz = self._center_MHz + (self._span_MHz / 2)
        self._frequencies_MHz = np.linspace(self._start_MHz,
                                            self._stop_MHz,
                                            self._numpts)
        
        self._last_power_spectrum_dBm = None
        self._capture_history_len = 2000
        self.capture_history = WaterfallModel(self._frequencies_MHz,
                                              self._capture_history_len)
        self._capture_count = 0
        
        self._capture_timer = QtCore.QTimer() #for app-side acquisition control
        self._capture_timer.timeout.connect(self._on_capture_timer)
        self.capturing = False
        
        self.reset()
    
    def _init_hardware(self, ip_address):
        self._driver = WSA()
        self._driver.connect(ip_address)
        
    def reset(self):
        """Sets a known start state."""
        
        #Set our app-specific reset state (802.11 range)
        center_frequency_MHz = 2447
        self._reset_hardware()
    
    def _reset_hardware(self):
        drv = self._driver
        drv.reset()
        drv.request_read_perm()
        drv.freq(self._center_MHz)
        drv.decimation(1) # do decimate
        drv.attenuator(0) # don't attenuate

    def start_continuous_capture(self, capture_interval_s):
        #It would be nice to be able to set the capture interval on the
        #device itself so that we aren't slave to lagging issues on the OS.
        
        #We could also just calculate the number of pts required to achieve
        #the required capture interval (or close enough), and have the
        #resulting frequiency grid, res bw, et al adjust accordingly. But...
        #clearly out of scope for this cheap abstraction.
        
        #Timing will be managed by a QTimer in this case. As a result,
        #capture_interval_s is really done on best effort (although the
        #QTimer drivign it does make reasonable efforts to sync timing).
        self._capture_timer.stop()
        self._capture_timer.start(1000 * capture_interval_s)
        self.capturing = True
        
    def stop_continuous_capture(self):
        self.capturing = False
        self._capture_timer.stop()
        
        
    def acquire_single_power_spectrum(self):
        STAIRS_MODE = False
        self._capture_count += 1
        
        if STAIRS_MODE:
            STAIR_WIDTH = 50
            stair_start = self._capture_count % self._numpts
            stair_start = np.floor(stair_start / STAIR_WIDTH) * STAIR_WIDTH
            stair_stop = stair_start + STAIR_WIDTH
            ps_dBm = np.zeros(self._numpts) - 80
            ps_dBm[stair_start:stair_stop] = -20
            timestamp_s = self._capture_count
        else:
            drv = self._driver
            vrt_data, context = read_data_and_context(drv, self._numpts)
            
            assert isinstance(vrt_data, pyrf.vrt.DataPacket)
            ps_dBm = compute_fft(drv, vrt_data, context, convert_to_dbm=True)
            
            #Accumulate history...
            timestamp_s = calc_vrt_sample_time_s(vrt_data)
        self.capture_history.add_row(ps_dBm, timestamp_s = timestamp_s)
        
        self._last_power_spectrum_dBm = ps_dBm
        return ps_dBm
    
    def _on_capture_timer(self):
        #grab a spectrum! The historical model will be updated and events can
        #be driven from that directly.
        self.acquire_single_power_spectrum()


class MockWSA(MyWifiWSA):
    def __init__(self, ip_address):
        super(MockWSA, self).__init__(None) #ip_address not used
        
        self._mu = self._center_MHz
        self._A = 2**10
        self._sigma = self._span_MHz / 50
        self._noise_floor = self._A / 100 #20 dB SNR
        self._step_MHz = self._span_MHz / len(self._frequencies_MHz)
        self._MU_WALK = 10 * self._step_MHz
        self._SIGMA_WALK = self._step_MHz
        
    def _init_hardware(self, ip_address):
        pass #we're mocking
    
    def _reset_hardware(self):
        pass #we're mocking
    
    def acquire_single_power_spectrum(self):
        A = self._A
        x_data = self._frequencies_MHz
        mu = self._mu
        sigma = self._sigma
        npts = len(self._frequencies_MHz)
        signal = A * np.exp(-np.power(x_data - mu, 2.) / (2 * np.power(sigma, 2.)))
        noise = np.random.random(npts) * self._noise_floor #white is good enough
        signal = signal + noise
        
        #toss in an occasional burst...
        if np.random.random() > 0.95:
            burst_mu = random.choice(self._frequencies_MHz)
            burst_sigma = self._sigma
            burst = A * np.exp(-np.power(x_data - burst_mu, 2.) / (2 * np.power(burst_sigma, 2.)))
            signal += burst
        
        #throw in some unconstrained random walk...
        if np.random.random() > 0.5:
            self._mu += self._MU_WALK
        else:
            self._mu -= self._MU_WALK
        
        if np.random.random() > 0.5:
            self._sigma += self._SIGMA_WALK
        else:
            self._sigma -= self._SIGMA_WALK
        
        signal_dBm = 10 * np.log10(signal / A)
        
        signal_dBm[-2] = 0
        signal_dBm[-1] = 0
        signal_dBm[0] = 0
        signal_dBm[1] = 0
        
        self.capture_history.add_row(signal_dBm)
        
        return signal_dBm


app = QtGui.QApplication(sys.argv)
main_win = MainWin()
main_win.show()

sys.exit(app.exec_())
