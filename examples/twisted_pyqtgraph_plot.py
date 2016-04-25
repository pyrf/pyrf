#!/usr/bin/env python

# import required libraries
from pyqtgraph.Qt import QtGui, QtCore
import pyqtgraph as pg
import sys
import numpy as np
from pyrf.devices.thinkrf import WSA
from pyrf.util import read_data_and_context
from pyrf.numpy_util import compute_fft
from pyrf.connectors.twisted_async import TwistedConnector

from twisted.internet import reactor, defer
import twisted.python.log

# plot constants
CENTER_FREQ = 2450 * 1e6 
SAMPLE_SIZE = 1024
ATTENUATOR = 0
DECIMATION = 4
RFE_MODE = 'ZIF'
TRIGGER_SET = {'type': 'None',
                'fstart': 2400 * 1e6,
                'fstop': 2500 * 1e6,
                'amplitude': -70}

# connect to WSA device
dut = WSA()
ip = sys.argv[1]
dut = WSA(connector=TwistedConnector(reactor))
win = pg.GraphicsWindow()
win.resize(1000,600)
win.setWindowTitle("PYRF FFT Plot Example")

@defer.inlineCallbacks
def show_i_q():
    yield dut.connect(sys.argv[1])

    # setup test conditions
    yield dut.reset()
    yield dut.request_read_perm()
    yield dut.rfe_mode(RFE_MODE)
    yield dut.freq(CENTER_FREQ)
    yield dut.decimation(0)
    yield dut.attenuator(ATTENUATOR)

    yield dut.trigger(TRIGGER_SET)
    dut.connector.vrt_callback = receive_vrt
    # capture 1 packet
    yield dut.capture(1024, 1)
context = {}
def receive_vrt(packet):
    # read until I get 1 data packet
    global context, dut
    if not packet.is_data_packet():
        context.update(packet.fields)
        return
    else:
        pow_data = compute_fft(dut, packet, context)
        print pow_data
        update(dut, pow_data)

# initialize plot
fft_plot = win.addPlot(title="Power Vs. Frequency")
# disable auto size of the x-y axis
fft_plot.enableAutoRange('xy', False)
curve = fft_plot.plot(pen='g')

def update(dut, pow_data):
    curve.setData(pow_data, pen = 'g')
    dut.capture(SAMPLE_SIZE, 1)
    
d = show_i_q()
d.addErrback(twisted.python.log.err)
reactor.run()

## Start Qt event loop unless running in interactive mode or using pyside.
if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
