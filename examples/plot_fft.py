#!/usr/bin/env python

from thinkrf.devices import WSA4000
from thinkrf.config import TriggerSettings

import sys
import time
import math

from numpy import fft, abs, log10
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
dut.capture(1024, 1)

# read until I get 1 data packet
while not dut.eof():
    pkt = dut.read()

    if pkt.is_data_packet():
        break

# seperate data into i and q
cdata = [complex(i, q) for i, q in pkt.data]

# compute the fft of the complex data
cfft = fft.fft(cdata)
cfft = fft.fftshift(cfft)

# compute power
powdata = log10(abs(cfft)) * 20

# setup my graph
fig = figure(1)
axis([0, 1024, 0, 200])
indexes = range(0, 1024)
for i in indexes:
    i = (i-512) * 125e6 / 1024/1024

xlabel("Sample Index")
ylabel("Amplitude")

# plot something
plot(powdata, color='blue')

# show graph
show()
