#!/usr/bin/env python

import sys
from pyrf.devices.thinkrf import WSA4000
import time

SAMPLES = 2**20

# connect to wsa
dut = WSA4000()
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
    dut.stream_start()
    start = time.time()
    for i in range(runs):
        while not dut.eof():
            pkt = dut.read()

            if pkt.is_data_packet():
                break
    dut.stream_stop()
    dut.flush()
    stop = time.time()
    print 'spp %d: %f samples/second' % (spp, spp*runs/(stop-start))
