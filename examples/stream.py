#!/usr/bin/env python

import sys
from pyrf.devices.thinkrf import WSA
import time

SAMPLES = 2**20

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])

# setup test conditions
dut.reset()
dut.request_read_perm()
dut.ifgain(0)
dut.freq(2450e6)
dut.gain('low')
dut.fshift(0)
dut.decimation(0)

for spp in [min(2**i, 2**16-16) for i in range(9, 17)]:
    dut.spp(spp)

    runs = max(SAMPLES/spp, 1)
    dut.stream_start(spp)
    start = None
    while True:
        pkt = dut.read()
        if pkt.is_context_packet() and pkt.fields.get('streamid') == spp:
            break
    start = time.time()
    for i in range(runs):
        while True:
            pkt = dut.read()
            if pkt.is_data_packet():
                break
    stop = time.time()
    dut.stream_stop()
    dut.flush()
    print 'spp %d: %f samples/second' % (spp, spp*runs/(stop-start))
