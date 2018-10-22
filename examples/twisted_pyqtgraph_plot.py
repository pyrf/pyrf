#!/usr/bin/env python

# import required libraries
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import sys
import numpy as np
from pyrf.devices.thinkrf import WSA
from pyrf.numpy_util import compute_fft

from pyrf.connectors.twisted_async import TwistedConnector

app = QtGui.QApplication([])
import qt4reactor
qt4reactor.install()

from twisted.internet import reactor, defer
import twisted.python.log

# plot constants
CENTER_FREQ = 2450 * 1e6
SAMPLE_SIZE = 1024
PPB = 1
ATTENUATOR = 0
DECIMATION = 1
RFE_MODE = 'ZIF'
TRIGGER_CONF = {'type': 'None',
                'fstart': 2400 * 1e6,
                'fstop': 2500 * 1e6,
                'amplitude': -70}

# get IP from command input
ip = sys.argv[1]

# confiture RTSA to use twisted
dut = WSA(connector=TwistedConnector(reactor))


# Setup the plotting window
class MainApplication(pg.GraphicsWindow):

    def __init__(self, dut):
        super(MainApplication, self).__init__()
        self.dut = dut

    # to ensure the reactor stopped when plot stopped
    def closeEvent(self, event):
        reactor.callLater(2 ** -4, reactor.stop)

# initialize plot
win = MainApplication(dut) #pg.GraphicsWindow()
win.resize(1000, 600)
win.setWindowTitle("PYRF FFT Plot Example")

fft_plot = win.addPlot(title="Power Vs. Frequency")
fft_plot.setLabel('bottom', text='Frequency', units='Hz', unitPrefix=None)
fft_plot.setLabel('left', text= 'Power', units = 'dBm', unitPrefix=None)
# autorange the first plot to get the y-axis range
fft_plot.enableAutoRange('xy', True)
curve = fft_plot.plot(pen='g')


@defer.inlineCallbacks
def show_i_q():
    yield dut.connect(ip)

    # setup test conditions
    yield dut.reset()
    yield dut.request_read_perm()
    yield dut.rfe_mode(RFE_MODE)
    yield dut.freq(CENTER_FREQ)
    yield dut.decimation(DECIMATION)
    yield dut.attenuator(ATTENUATOR)
    yield dut.trigger(TRIGGER_CONF)
    # add callback
    dut.connector.vrt_callback = receive_vrt
    yield dut.capture(SAMPLE_SIZE, PPB)

context = {}
def receive_vrt(packet):
    # read until get 1 data packet
    global dut, context
    if not packet.is_data_packet():
        context.update(packet.fields)
        return
    else:
        pow_data = compute_fft(dut, packet, context)
        update(dut, pow_data)
        # now disable the range to prevent fluctuation
        fft_plot.enableAutoRange('xy', False)


def update(dut, pow_data):
    curve.setData(pow_data, pen = 'g')
    dut.capture(SAMPLE_SIZE, PPB)

d = show_i_q()
d.addErrback(twisted.python.log.err)
reactor.run()
