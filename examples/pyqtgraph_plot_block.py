#!/usr/bin/env python

#####################################################################
## This example makes use of capture_spectrum() of util.py to
## perform a single block capture of desire RBW and plot the
## computed spectral data within the usuable frequency range
##
## See thinkrf.py for other data capture functions, especially if
## raw data capture (with context info output) is preferred
#####################################################################

# import required libraries
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import sys
import numpy as np
from pyrf.devices.thinkrf import WSA
from pyrf.util import capture_spectrum

# Constants for configuration
RFE_MODE = 'SH'
CENTER_FREQ = 2450 * 1e6
SPP = 16384
PPB = 1
RBW = 125e6 / (SPP * PPB)  # 125 MHz is the sampling rate
AVERAGE = 1
DECIMATION = 1 # no decimation
ATTENUATION = 0
GAIN = 'HIGH'
TRIGGER_SETTING = {'type': 'NONE',
                'fstart': (CENTER_FREQ - 10e6), # some value
                'fstop': (CENTER_FREQ + 10e6),  # some value
                'amplitude': -100}

# Setup the plotting window
class MainApplication(pg.GraphicsWindow):

    def __init__(self, dut):
        super(MainApplication, self).__init__()
        self.dut = dut

    # to do SCPI command on the run
    def keyPressEvent(self, event):
        if event.text() == ';':
            cmd, ok = QtGui.QInputDialog.getText(win, 'Enter SCPI Command',
                        'Enter SCPI Command:')
            if ok:
                if '?' not in cmd:
                    dut.scpiset(cmd)

# initialize an RTSA (aka WSA) device handle
dut = WSA()
win = MainApplication(dut)

# get device's IP and connect
if len(sys.argv) > 1:
    ip = sys.argv[1]
else:
    ip, ok = QtGui.QInputDialog.getText(win, 'Open Device',
                'Enter a hostname or IP address:')
dut.connect(ip)

# initialize RTSA configurations
dut.reset()
dut.request_read_perm()
dut.rfe_mode(RFE_MODE)
dut.freq(CENTER_FREQ)
dut.attenuator(ATTENUATION)
dut.psfm_gain(GAIN)
dut.trigger(TRIGGER_SETTING)

# initialize the plot
win.resize(1000, 600)
win.setWindowTitle("PYRF FFT Plot Example - " + ip)
fft_plot = win.addPlot(title="Power Vs. Frequency")
fft_plot.enableAutoRange('xy', True)
curve = fft_plot.plot(pen='g')
fft_plot.setLabel('left', text='Power', units='dBm', unitPrefix=None)
fft_plot.setLabel('bottom', text='Frequency', units='Hz', unitPrefix=None)

# initialize the y-axis of the plot
plot_ymin = -130
plot_ymax = 10
fft_plot.setYRange(plot_ymin, plot_ymax)

# Get data and plot
def update():
    global dut, curve, fft_plot, fstart, fstop, print_once

    # get spectral data with a given RBW and plot
    fstart, fstop, pow_data = capture_spectrum(dut, RBW, AVERAGE, DECIMATION)
    freq_range = np.linspace(fstart , fstop, len(pow_data))
    curve.setData(freq_range, pow_data, pen='g')
    fft_plot.enableAutoRange('xy', False)

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(0)


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
