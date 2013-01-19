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
    yield dut.ifgain(0)
    yield dut.freq(2450e6)
    yield dut.gain('low')
    yield dut.fshift(0)
    yield dut.decimation(0)

    # capture 1 packet
    yield dut.capture(1024, 1)

    # read until I get 1 data packet
    while not dut.eof():
        pkt = yield dut.read()

        if pkt.is_data_packet():
            break

    # print I/Q data into i and q
    for i, q in pkt.data:
        print "%d,%d" % (i, q)

d = show_i_q()
d.addErrback(twisted.python.log.err)
d.addCallback(lambda _:reactor.stop())
reactor.run()
