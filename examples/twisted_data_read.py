#!/usr/bin/env python

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
        dut.capture(SAMPLE_SIZE, 1)
        

    
    
d = show_i_q()
d.addErrback(twisted.python.log.err)
reactor.run()
