#!/usr/bin/env python

from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice

import sys
import time
import math

from matplotlib.pyplot import plot, figure, axis, xlabel, ylabel, show
import numpy as np

# declare sweep constants
START_FREQ = 50e6
STOP_FREQ = 8e9
RBW = 100e3

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])
dut.request_read_perm()
# declare sweep device
sd = SweepDevice(dut)

# read the spectral data
fstart, fstop, spectra_data = sd.capture_power_spectrum(START_FREQ, STOP_FREQ, RBW,
    {'attenuator':0})


# setup my graph
fig = figure(1)
xvalues = np.linspace(fstart, fstop, len(spectra_data))

xlabel("Frequency")
ylabel("Amplitude")

# plot something
plot(xvalues, spectra_data, color='blue')

# show graph
show()
