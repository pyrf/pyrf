#!/usr/bin/env python

import sys
from pyrf.devices.thinkrf import WSA

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])

# setup data capture conditions
dut.reset()
dut.request_read_perm()
dut.freq(2450e6)

# capture 1 packet of 1024 data points
dut.capture(1024, 1)

# read until 1 data packet is received
while not dut.eof():
    pkt = dut.read()

    if pkt.is_data_packet():
        break

# print I/Q data into i and q
for i, q in pkt.data:
    print "%d,%d" % (i, q)
