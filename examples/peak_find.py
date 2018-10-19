#!/usr/bin/env python

import sys
from pyrf.devices.thinkrf import WSA

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])

# setup test conditions
dut.reset()
dut.freq(2450e6)

peak_lost = dut.peakfind(n = 5)

for peak in peak_lost :
    print peak
