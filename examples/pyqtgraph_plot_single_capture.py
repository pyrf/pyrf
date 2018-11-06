#!/usr/bin/env python

#####################################################################
## This example makes use of read_data() of thinkrf.py to perform
## a single capture of SPP sample size, and plot the spectral result
#####################################################################

# import required libraries
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import sys
import numpy as np
from pyrf.devices.thinkrf import WSA

# Device configuration constants
CENTER_FREQ = 930 * 1e6
SAMPLE_SIZE = 8192
ATTENUATOR = 0
DECIMATION = 1
RFE_MODE = 'SH'
MHZ = 1e6

class MainApplication(pg.GraphicsWindow):
    def __init__(self, dut):
        super(MainApplication, self).__init__()
        self.dut = dut

    # press ';' to manually enter a scpi command
    def keyPressEvent(self, event):
        if event.text() == ';':
            cmd, ok = QtGui.QInputDialog.getText(win, 'Enter SCPI Command',
                        'Enter SCPI Command:')
            if ok:
                if '?' not in cmd:
                    dut.scpiset(cmd)

# get RTSA device IP
if len(sys.argv) > 1:
    ip = sys.argv[1]
else:
    ip, ok = QtGui.QInputDialog.getText(win, 'Open Device',
                'Enter a hostname or IP address:')

# connect to an RTSA device
dut = WSA()
dut.connect(ip)

# initialize RTSA configurations
dut.reset()
dut.request_read_perm()
dut.freq(CENTER_FREQ)
dut.decimation(DECIMATION)
dut.attenuator(ATTENUATOR)
dut.rfe_mode(RFE_MODE)

# initialize plot
win = MainApplication(dut)
win.resize(1000,600)
win.setWindowTitle("PYRF FFT Plot Example - " + ip)
fft_plot = win.addPlot(title="Power Vs. Frequency")

# initialize x-axes limits
BANDWIDTH = dut.properties.FULL_BW[RFE_MODE]
# for SH/SHN mode, spectral inversion and IF centred at 35 MHz (not 62.5 MHz/ 2) affect the display
if ((RFE_MODE == 'SH') | (RFE_MODE == 'SHN')):
    spec_inv = int(dut.scpiget("FREQ:INV? %d" % CENTER_FREQ))
    if spec_inv:
        plot_xmin = (CENTER_FREQ) - (62.5 - 35) * MHZ
        plot_xmax = (CENTER_FREQ) + (35 * MHZ)
    else:
        plot_xmin = (CENTER_FREQ) - (35 * MHZ)
        plot_xmax = (CENTER_FREQ) + (62.5 - 35) * MHZ
else:
    plot_xmin = (CENTER_FREQ) - (BANDWIDTH / 2)
    plot_xmax = (CENTER_FREQ) + (BANDWIDTH / 2)

fft_plot.setLabel('bottom', text='Frequency', units='Hz', unitPrefix=None)

# initialize the y-axis of the plot
plot_ymin = -130
plot_ymax = 20
fft_plot.setYRange(plot_ymin ,plot_ymax)
fft_plot.setLabel('left', text= 'Power', units = 'dBm', unitPrefix=None)

# enable auto size of the x-y axis
fft_plot.enableAutoRange('xy', True)

# initialize a curve for the plot
curve = fft_plot.plot(pen='g')
data, context, pow_data = dut.read_data(SAMPLE_SIZE)
freq_range = np.linspace(plot_xmin , plot_xmax, len(pow_data))


# get data and plot
def update():
    global dut, curve, fft_plot, plot_xmin, plot_xmax

    # read data
    data, context, pow_data = dut.read_data(SAMPLE_SIZE)

    curve.setData(freq_range, pow_data, pen = 'g')
    fft_plot.enableAutoRange('xy', False)

timer = QtCore.QTimer()
timer.timeout.connect(update)
timer.start(0)


## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
