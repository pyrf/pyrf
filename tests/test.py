#!/usr/bin/python

import sys
import time
import matplotlib.pyplot as plt
from agilent.devices import N5183
from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice


show_plot = False
save_data = False
fin = None
mode = 'SH'
pin = -30

ip = sys.argv[1]
if len(sys.argv) >= 2:
    fstart = float(sys.argv[2])
if len(sys.argv) >= 3:
    fstop = float(sys.argv[3])
if len(sys.argv) >= 4:
    rbw = float(sys.argv[4])
if len(sys.argv) >= 5:
    fin = float(sys.argv[5])

if save_data:
    reqstart = fstart
    reqstop = fstop
    reqrbw = rbw

# connect to wsa
dut = WSA()
dut.connect(ip)
dut.scpiset("*RST")
dut.flush()

# create sweep device
sd = SweepDevice(dut)
sd.logtype = 'PRINT'

# setup siggen
if fin:
    sg = N5183("10.126.110.19")
    sg.amplitude(pin)
    sg.freq(fin)
    sg.output(1)
    time.sleep(0.05)

# capture spectrum
(fstart, fstop, data) = sd.capture_power_spectrum(fstart, fstop, rbw, { }, mode)
calcrbw = (fstop - fstart) / len(data)
print "fstart = %d, fstop = %d, datalen = %d, calculated rbw = %f" % (fstart, fstop, len(data), calcrbw)

# search for max
m = max(data)
peak = [i for i, j in enumerate(data) if j == m]
peak = peak[0]
fpeak = int((peak * calcrbw) + fstart)
print "Peak found at index %d, %f dBm at %d Hz" % (peak, m, fpeak)
print "- d(freq) = %d, d(amp) = %0.1f" % (abs(fpeak - fin), abs(m - pin))

# plot result
if show_plot:
    f = fstart
    freq = [ ]
    power = [ ]
    for d in data:

        # write the line
        freq.append(f / 1e6)

        power.append(d)

        # inc f
        f = f + calcrbw

    plt.axis([freq[0], freq[-1], -150, 0])
    plt.axvline(x = fin / 1e6, color='#ff0000')
    plt.plot(freq, power)
    plt.show()

if save_data:
    filename = "data-%d-%d-%d-%d-%s.dat" % (fstart, fstop, int(rbw), fin, mode)
    fp = open(filename, "w+")

    fp.write("Requested: fstart/fstop/rbw: %d / %d / %d\n" % (reqstart, reqstop, reqrbw))
    fp.write("Actual:    fstart/fstop/rbw: %d / %d / %d\n" % (fstart, fstop, calcrbw))
    fp.write("\n")

    f = fstart
    i = 0
    for d in data:
        
        # print line headers
        if (i % 8) == 0:
            fp.write("%12.3f : " % f)

        # print value
        fp.write("%5.1f" % d)

        # print comma or newline
        if (i % 8) == 7:
            fp.write("\n")
        else:
            fp.write(", ")

        # inc
        f += calcrbw
        i += 1

    fp.write("\n")
    fp.close()
