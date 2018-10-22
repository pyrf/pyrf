#!/usr/bin/env python

import sys
import time
import math
import numpy as np
from pyrf.devices.thinkrf import WSA
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.sweep_device import SweepDevice
from matplotlib.pyplot import plot, figure, axis, xlabel, ylabel, show

from twisted.internet import reactor, defer
import twisted.python.log

START_FREQ = 0e6
STOP_FREQ = 8e9
RBW = 100e3

def plot_sweep(fstart, fstop, bins):
    # setup my graph
    fig = figure(1)
    xvalues = np.linspace(fstart, fstop, len(bins))

    xlabel("Frequency")
    ylabel("Amplitude")

    # plot something
    plot(xvalues, bins, color='blue')

    # show graph
    show()
    reactor.callLater(2 ** -4, reactor.stop)

@defer.inlineCallbacks
def start_sweep(v):
    global sd
    sd = SweepDevice(dut, plot_sweep)
    fstart, fstop, spectral_data = sd.capture_power_spectrum(START_FREQ, STOP_FREQ, RBW, {'attenuator': 0 })

# configure RTSA to use twisted
dut = WSA(connector=TwistedConnector(reactor))

# connect to RTSA and configure
d = dut.connect(sys.argv[1])
d.addCallbacks(start_sweep, twisted.python.log.err)
reactor.run()
