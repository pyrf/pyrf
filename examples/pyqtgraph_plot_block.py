#!/usr/bin/env python

# import required libraries
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import sys
import numpy as np
from pyrf.devices.thinkrf import WSA
from pyrf.util import read_data_and_context
from pyrf.numpy_util import compute_fft


# plot constants
CENTER_FREQ = 2450 * 1e6 
SAMPLE_SIZE = 1024
ATTENUATOR = 1
DECIMATION = 1
RFE_MODE = 'ZIF'


# connect to WSA device
dut = WSA()
ip = sys.argv[1]
dut.connect(ip)

class MainApplication(pg.GraphicsWindow):

    def __init__(self, dut):
        super(MainApplication, self).__init__()
        self.dut = dut

    def keyPressEvent(self, event):
        if event.text() == ';':
            cmd, ok = QtGui.QInputDialog.getText(win, 'Enter SCPI Command',
                        'Enter SCPI Command:')
            if ok:
                if '?' not in cmd:
                    dut.scpiset(cmd)

win = MainApplication(dut)
win.resize(1000,600)
win.setWindowTitle("PYRF FFT Plot Example")


# initialize WSA configurations
dut.reset()
dut.request_read_perm()
dut.freq(CENTER_FREQ)
dut.decimation(DECIMATION)
dut.attenuator(ATTENUATOR)
dut.rfe_mode(RFE_MODE)

BANDWIDTH = dut.properties.FULL_BW[RFE_MODE]
# initialize plot
fft_plot = win.addPlot(title="Power Vs. Frequency")

# initialize x-axes limits
plot_xmin = (CENTER_FREQ) - (BANDWIDTH  / 2)
plot_xmax = (CENTER_FREQ) + (BANDWIDTH / 2)
fft_plot.setLabel('left', text= 'Power', units = 'dBm', unitPrefix=None)

# initialize the y-axis of the plot
plot_ymin = -130
plot_ymax = 20
fft_plot.setYRange(plot_ymin ,plot_ymax)
fft_plot.setLabel('left', text= 'Power', units = 'dBm', unitPrefix=None)

# disable auto size of the x-y axis
fft_plot.enableAutoRange('xy', False)

# initialize a curve for the plot 
curve = fft_plot.plot(pen='g')

def update():
    global dut, curve, fft_plot, plot_xmin, plot_xmax
    
    # read data
    data, context = read_data_and_context(dut, SAMPLE_SIZE)
    # compute the fft and plot the data
    pow_data = compute_fft(dut, data, context)

    # update the frequency range (Hz)
    freq_range = np.linspace(plot_xmin , plot_xmax, len(pow_data))
    
    # initialize the x-axis of the plot
    fft_plot.setXRange(plot_xmin,plot_xmax)
    fft_plot.setLabel('bottom', text= 'Frequency', units = 'Hz', unitPrefix=None)

    curve.setData(freq_range,pow_data, pen = 'g')

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(0)

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
