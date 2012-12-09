#!/usr/bin/env python

from thinkrf.devices import WSA4000
from thinkrf.config import TriggerSettings
from thinkrf.util import read_data_and_reflevel
from thinkrf.numpy_util import compute_fft

import sys
import time
import math

from matplotlib.pyplot import plot, figure, axis, xlabel, ylabel, show

# connect to wsa
dut = WSA4000()
dut.connect(sys.argv[1])

# setup test conditions
dut.reset()
dut.request_read_perm()
dut.ifgain(0)
dut.freq(2450e6)
dut.gain('high')
dut.fshift(0)
dut.decimation(0)
trigger = TriggerSettings(
    trigtype="LEVEL",
    fstart=2400e6,
    fstop=2480e6,
    amplitude=-70)
dut.trigger(trigger)

# capture 1 packet
data, reflevel = read_data_and_reflevel(dut, 1024)

# compute the fft of the complex data
powdata = compute_fft(dut, data, reflevel)

# setup my graph
fig = figure(1)
axis([0, 1024, -120, 20])

xlabel("Sample Index")
ylabel("Amplitude")

# plot something
plot(powdata, color='blue')

# show graph
show()
