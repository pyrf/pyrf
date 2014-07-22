#!/usr/bin/env python

import collections
import threading
import time
import itertools
import ctypes
import Queue

# import required libraries
from PySide import QtGui, QtCore
import pyqtgraph as pg
import pyqtgraph.functions as pgfuncs
import sys
import numpy as np
import pyrf
from pyrf.devices.thinkrf import WSA
from pyrf.util import read_data_and_context, collect_data_and_context
from pyrf.numpy_util import compute_fft
from pyrf.gui.waterfall_widget import (ThreadedWaterfallPlotWidget,
                                       WaterfallModel)


class WaterfallCrosshairDemoApp(QtGui.QMainWindow):
    def __init__(self, wsa_ip_address):
        super(WaterfallCrosshairDemoApp, self).__init__()
        self.resize(1500, 1000)
        
        self.wsa = MyWifiWSA(wsa_ip_address)
        
        #self.resize(300, 300)
        self.DoCreateWidgets()
        self.DoLayout()
        self.DoHandlers()
        
        self._capture_period_s = 0.05
        self.wsa.start_continuous_capture(self._capture_period_s)
    
    def DoCreateWidgets(self):
        self._main_wid = QtGui.QWidget()
        
        self._waterfall = ThreadedWaterfallPlotWidget(
            self.wsa.capture_history,
            scale_limits=(-140, -50),
            max_frame_rate_fps=40,
            parent=self._main_wid,
        )
        
        self._live_plot = pg.PlotWidget(self._main_wid)
        self._live_plot.setLabel('bottom', text = 'Frequency', units = 'Hz')
        self._live_plot.setYRange(-160, 20)
        self._live_plot.setLabel('left', text = 'Power', units = 'dBm')
        self._live_curve = self._live_plot.plot(pen='b')
        
        self._vslice_plot = pg.PlotWidget(self._main_wid)
        self._vslice_plot.setLabel('bottom', text = 'Time', units = 's')
        self._vslice_plot.setLabel('left', text = 'Power', units = 'dBm')
        self._vslice_curve = self._vslice_plot.plot(pen='r')

        self._hslice_plot = pg.PlotWidget(self._main_wid)
        self._hslice_plot.setLabel('bottom', text = 'Frequency', units = 'Hz')
        self._hslice_plot.setLabel('left', text = 'Power', units = 'dBm')
        self._hslice_curve = self._hslice_plot.plot(pen='r')
        
        self._start_but = QtGui.QPushButton("Pause capture")
        
    def DoLayout(self):
        layout = QtGui.QGridLayout(self._main_wid)
        layout.addWidget(self._live_plot, 0, 0)
        layout.addWidget(self._waterfall, 1, 0)
        layout.addWidget(self._hslice_plot, 2, 0)
        
        layout.addWidget(self._start_but, 0, 1)
        layout.addWidget(self._vslice_plot, 1, 1)

        #layout = QtGui.QVBoxLayout(self._main_wid)
        #layout.addWidget(self._live_plot)
        #layout.addWidget(self._waterfall)
        #layout.addWidget(self._start_but)
        
        self.setCentralWidget(self._main_wid)
    
    def DoHandlers(self):
        #self._waterfall.sigMouseMoved.connect(self.onWaterfallMouseMove)
        self.wsa.capture_history.sigNewDataRow.connect(self.onNewDataRow)
        self._start_but.clicked.connect(self.onStartButton)
        self._waterfall.sigMouseMoved.connect(self.onWaterfallMouseMove)
    
    def onWaterfallMouseMove(self, x, y, hslice, vslice):
        hx, hy = hslice
        if np.min(hx) != np.NINF:
            self._hslice_plot.setXRange(np.min(hx), np.max(hx))
            self._hslice_plot.setYRange(np.min(hy), np.max(hy))
            self._hslice_curve.setData(*hslice)
        
        vx, vy = vslice
        if np.min(vy) != np.NINF:
            min_vx = np.min(vx)
            max_vx = np.max(vx)
            if min_vx != max_vx:
                self._vslice_plot.setXRange(min_vx, max_vx)
                
            min_vy = np.min(vy)
            max_vy = np.max(vy)
            if min_vy != max_vy:
                self._vslice_plot.setYRange(min_vy, max_vy)
            
            self._vslice_curve.setData(*vslice)
    
    def onStartButton(self):
        if self.wsa.capturing:
            self.wsa.stop_continuous_capture()
            self._start_but.setText("Start capture")
        else:
            self.wsa.start_continuous_capture(self._capture_period_s)
            self._start_but.setText("Pause capture")
        
    def onNewDataRow(self, data_tuple):
        time_s, data, metadata = data_tuple
        
        f = self.wsa._frequencies_MHz
        p = data
        assert f.shape == p.shape
        
        self._live_plot.setXRange(np.min(f), np.max(f))
        self._live_curve.setData(x = f, y = p)


def calc_vrt_sample_time_s(vrt_data):
    return vrt_data.tsi + vrt_data.tsf * 1e-12

# plot/config constants
class MyWifiWSA(object):
    """A cheap/simple/incomplete WSA instrument abstraction.
    
    Hides driver internals that people using the device as a spectrum
    analyzer may not care about.
    
    """
    def __init__(self, ip_address):
        self._driver = WSA()
        self._driver.connect(ip_address)
        
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
    
    def reset(self):
        """Sets a known start state."""
        drv = self._driver
        
        #Set our app-specific reset state (802.11 range)
        center_frequency_MHz = 2447
        
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
        self._capture_timer.start(capture_interval_s)
        self.capturing = True
        
    def stop_continuous_capture(self):
        self.capturing = False
        self._capture_timer.stop()
        
        
    def acquire_single_power_spectrum(self):
        global STAIRS_MODE
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

STAIRS_MODE = False

app = QtGui.QApplication(sys.argv)
app.setGraphicsSystem("native") #hmm... experimenting
ip_address = sys.argv[1]
main_win = WaterfallCrosshairDemoApp(ip_address)
main_win.show()

exit_code = app.exec_()
sys.exit(exit_code)

