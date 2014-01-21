#!/usr/bin/env python

from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice

import sys
import time
import math

from matplotlib.pyplot import plot, figure, axis, xlabel, ylabel, show
import numpy as np

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])
dut.request_read_perm()
sd = SweepDevice(dut)

fstart, fstop, bins = sd.capture_power_spectrum(0e6, 20000e6, 5e6,
    {'attenuator':0})


# setup my graph
fig = figure(1)
xvalues = np.linspace(fstart, fstop, len(bins))

xlabel("Frequency")
ylabel("Amplitude")

# plot something
plot(xvalues, bins, color='blue')

# show graph
show()
