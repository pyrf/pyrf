#!/usr/bin/python

# import required libraries
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import sys
import numpy as np
import pyrf
from pyrf.gui.persistence_plot_widget import PersistencePlotWidget

import collections
import threading
import time

NPTS = 1024
x_data = np.arange(NPTS)

class MainWin(QtGui.QMainWindow):
    def __init__(self):
        super(MainWin, self).__init__()
        self.resize(1600, 900)
        self.DoCreateWidgets()
        self.DoLayout()
        self.DoHandlers()
    
    def DoCreateWidgets(self):
        global data_model
        self._main_wid = QtGui.QWidget()
        self._pltSpectrum = pg.PlotWidget(self)
        #self._pltPersist = pg.PlotWidget(self)
        self._pltPersist = PersistencePlotWidget(self)
        
        self._pltPersist.setXRange(0, NPTS, padding=0)
        self._pltPersist.setYRange(0, 0)
        
        self._gradient_editor = self._pltPersist.gradient_editor
        #self._gradient_editor = None
    
    
    def DoLayout(self):
        layout = QtGui.QVBoxLayout(self._main_wid)
        layout.addWidget(self._pltSpectrum)
        if self._gradient_editor:
            layout.addWidget(self._gradient_editor)
        layout.addWidget(self._pltPersist)
        
        self.setCentralWidget(self._main_wid)
    
    def DoHandlers(self):
        #self._waterfall.sigMouseMoved.connect(self.onWaterfallMouseMove)
        #self._start_but.clicked.connect(self.onStartButton)
        pass


img=None
do_update = True
img_array = None
def update():
    global NPTS, data_model, do_update
    global data_model
    global img #haaaack
    global img_array
    
    #data = np.random.normal(size = (NPTS, ))
    if do_update:
        #do_update=False
        plt = main_win._pltSpectrum
        data = get_signal()
        plt.plot(x = x_data, y=data, clear = True)
        #plt.hideAxis("left")
        #plt.hideAxis("bottom")
        plt.setXRange(0, NPTS, padding=0)
        plt.setYRange(-50, 0)
        
        #Now for the persistence plot...
        main_win._pltPersist.setXRange(0, NPTS, padding=0)
        main_win._pltPersist.setYRange(-50, 0)
        main_win._pltPersist.plot(x = x_data, y=data)


mu = NPTS/2.
sigma = NPTS/50.
A = 2**10
noise_floor = A/100 #20 dB SNR
MU_WALK = 10
SIGMA_WALK = 1
def get_signal():
    global A, mu, sigma
    signal = A * np.exp(-np.power(x_data - mu, 2.) / (2 * np.power(sigma, 2.)))
    noise = np.random.random(NPTS) * noise_floor #white is good enough
    signal = signal + noise
    
    if np.random.random() > 0.98:
        burst_mu = (NPTS / 4)
        burst_sigma = NPTS / 50
        burst = A * np.exp(-np.power(x_data - burst_mu, 2.) / (2 * np.power(burst_sigma, 2.)))
        signal += burst
    
    signal = 10 * np.log10(signal / A)
    #throw in some unconstrained random walk...
    mu += MU_WALK if np.random.random() > 0.5 else -MU_WALK
    sigma += SIGMA_WALK if np.random.random() > 0.5 else -SIGMA_WALK
    
    return signal

app = QtGui.QApplication(sys.argv)
main_win = MainWin()
main_win.show()

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(100)


sys.exit(app.exec_())

print "foooo!"
