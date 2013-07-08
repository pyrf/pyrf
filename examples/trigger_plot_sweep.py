#!/usr/bin/env python

from pyrf.devices.thinkrf import WSA4000
from pyrf.sweep_device import SweepDevice
from pyrf.config import TriggerSettings

import sys
import time
import math

from matplotlib.pyplot import plot, figure, axis, xlabel, ylabel, show
import numpy as np

# connect to wsa
dut = WSA4000()
dut.connect(sys.argv[1])
sd = SweepDevice(dut)

fstart, fstop, bins = sd.capture_power_spectrum(2.4e9, 2.5e9, 2000,
    {'gain': 'high', 'antenna': 1},
    [TriggerSettings('LEVEL', 2.4e9, 2.5e9, -70)])

# setup my graph
fig = figure(1)
xvalues = np.linspace(fstart, fstop, len(bins))

xlabel("Frequency")
ylabel("Amplitude")

# plot something
plot(xvalues, bins, color='blue')

# show graph
show()
