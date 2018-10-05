#!/usr/bin/env python

#####################################################################
## This example shows an example of stream capture
## See the product's Programmer's Guide for info on Stream feature
#####################################################################


# import required libraries
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
DECIMATION = 1
RFE_MODE = 'ZIF'
TRIGGER_SET = {'type': 'None',
                'fstart': 2400 * 1e6,
                'fstop': 2500 * 1e6,
                'amplitude': -70}

# connect to WSA device
dut = WSA()
ip = sys.argv[1]
dut = WSA(connector=TwistedConnector(reactor))

class VRT_PRINTER():
    def print_packet(self, packet):
        print packet

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
    printer = VRT_PRINTER()

    dut.connector.vrt_callback = printer.print_packet

    # capture 1 packet
    yield dut.stream_start()

def stopStreaming():
    print 'stopped stream'
    dut.stream_stop()
    dut.flush()

import atexit
atexit.register(stopStreaming)

d = show_i_q()
d.addErrback(twisted.python.log.err)
reactor.run()
