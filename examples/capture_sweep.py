#!/usr/bin/env python

from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice

import sys
import time
import math

import numpy as np

# declare sweep constants
START_FREQ = 2300e6
STOP_FREQ = 2400e6
RBW = 10e3

# connect to WSA, and initialize device
init_time = time.time()
dut = WSA()
dut.connect('10.126.110.107')

dut.flush()
dut.abort()
dut.request_read_perm()
dut.reset()
dut.var_attenuator(0)

sd = SweepDevice(dut)
init_time = time.time() - init_time

# capture the sweep data

while True:
    capture_time = time.time()
    fstart, fstop, spectra_data = sd.capture_power_spectrum(START_FREQ, 
                                STOP_FREQ, 
                                RBW,
                                {'attenuator':0},
                                mode = 'SH')
    print np.mean(spectra_data)
    capture_time = time.time() - capture_time

    print 'Init Time (msec): ', init_time
    print 'Capture Time (msec): ', capture_time
    print  'Total Time (msec): ', init_time + capture_time 


