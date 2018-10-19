#!/usr/bin/env python

from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice
from pyrf.numpy_util import calculate_channel_power

import sys
import time
import math

from matplotlib.pyplot import plot, figure, axis, xlabel, ylabel, show
import numpy as np

def smooth(list,degree=1):
    new_list = []
    list_average = np.mean(sorted(list)[int(0.995 * len(list)):-1]) + 5
    for n, i in enumerate(list):

        start = max(0, n - degree)
        stop = min(len(list), n + degree)
        points = list[start:stop]
        if list[n] > list_average:
            new_list.append(list[n])
        else:
            new_list.append(np.mean(points))

    return new_list

# declare sweep constants
START_FREQ = 50e6
STOP_FREQ = 8e9
RBW = 100e3
VBW = 100e3

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])
dut.request_read_perm()
# declare sweep device
sd = SweepDevice(dut)

# read the spectral data
fstart, fstop, spectra_data = sd.capture_power_spectrum(START_FREQ, STOP_FREQ, RBW,
    {'attenuator':0})

# apply the VBW algorith
spectra_data = smooth(spectra_data, max(1, RBW/VBW))

# calculate the channel power
linear = np.power(10, np.divide(spectra_data,20))
channel_power = 10 * np.log10(np.sum(np.square(linear)))

print channel_power
fig = figure(1)
xvalues = np.linspace(fstart, fstop, len(spectra_data))

xlabel("Frequency")
ylabel("Amplitude")

# plot something
plot(xvalues, spectra_data, color='blue')

# show graph
show()
