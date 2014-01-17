#!/usr/bin/env python

import sys
from pyrf.devices.thinkrf import WSA4000
from pyrf.connectors.twisted_async import TwistedConnector

from twisted.internet import reactor, defer
import twisted.python.log

# connect to wsa
dut = WSA4000(connector=TwistedConnector(reactor))

@defer.inlineCallbacks
def show_i_q():
    yield dut.connect(sys.argv[1])

    # setup test conditions
    yield dut.reset()
    yield dut.request_read_perm()
    yield dut.freq(2450e6)
    yield dut.decimation(0)

    dut.connector.vrt_callback = receive_vrt
    # capture 1 packet
    yield dut.capture(1024, 1)

def receive_vrt(packet):
    # read until I get 1 data packet
    if not packet.is_data_packet():
        return

    # print I/Q data into i and q
    for i, q in packet.data:
        print "%d,%d" % (i, q)
    # exit
    reactor.stop()

d = show_i_q()
d.addErrback(twisted.python.log.err)
reactor.run()
