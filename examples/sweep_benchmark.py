#!/usr/bin/env python

import sys
from pyrf.devices.thinkrf import WSA
from pyrf.config import SweepEntry
import time

SAMPLES = 2**20
M = 1000000

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])

# setup test conditions
dut.reset()
dut.request_read_perm()

for spp in [min(2**i, 2**16-16) for i in range(9, 17)]:
    dut.abort()
    dut.flush()
    dut.sweep_clear()
    s = SweepEntry(
        fstart=100 * M,
        fstop=7900 * M,
        fstep=100 * M,
        fshift=0,
        decimation=1,
        spp=spp,
        ppb=1,
        )
    dut.sweep_add(s)
    captures = max(SAMPLES/spp, 1)
    dut.sweep_iterations(0) # continuous
    dut.sweep_start(spp)
    start = None
    while True:
        pkt = dut.read()
        if pkt.is_context_packet() and pkt.fields.get('sweepid') == spp:
            break
    start = time.time()
    for i in xrange(captures):
        while True:
            pkt = dut.read()
            if pkt.is_data_packet():
                break
    stop = time.time()
    dut.sweep_stop()
    dut.flush()
    print 'spp %5d: %6.1f GHz/second (%4d packets, %4.1fs,  %10.1f samples/s)' % (
        spp,
        100 * M * captures / (stop - start) / 1e9,
        captures,
        (stop - start),
        spp * captures / (stop - start))
