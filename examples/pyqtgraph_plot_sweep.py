#!/usr/bin/env python

# import required libraries
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import sys
import numpy as np
from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice

# plot constants
ATTENUATOR = 0
DECIMATION = 1
RFE_MODE = 'SH'

# declare sweep constants
START_FREQ = 20e6
STOP_FREQ = 200e6
RBW = 3e3


# connect to WSA device
dut = WSA()
win = pg.GraphicsWindow()
win.resize(1000,600)
win.setWindowTitle("PYRF FFT Plot Example")


ip = '10.126.110.111'

dut.connect(ip)

# initialize WSA configurations
dut.flush()
dut.abort()
dut.request_read_perm()
dut.reset()
sd = SweepDevice(dut)

# initialize plot
fft_plot = win.addPlot(title="Power Vs. Frequency")

# initialize x-axes limits
fft_plot.setLabel('left', text= 'Power', units = 'dBm', unitPrefix=None)

# initialize the y-axis of the plot
plot_ymin = -130
plot_ymax = 20
fft_plot.setYRange(plot_ymin ,plot_ymax)
fft_plot.setLabel('left', text= 'Power', units = 'dBm', unitPrefix=None)

# enable auto size of the x-y axis
fft_plot.enableAutoRange('xy', True)

# initialize a curve for the plot 
curve = fft_plot.plot(pen='g')

def update():
    global sd, curve, fft_plot, plot_xmin, plot_xmax

    # read data
    fstart, fstop, spectral_data = sd.capture_power_spectrum(START_FREQ, 
                                STOP_FREQ, 
                                RBW,
                                {'attenuator':0},
                                mode = 'SH')

    curve.setData(spectral_data, pen = 'g')
    fft_plot.enableAutoRange('xy', False)

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(0)


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
