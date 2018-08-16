#!/usr/bin/python

import sys
import time
import random
from agilent.devices import N5183
from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice

numtrials = 100000
pin = -30
pass_amp = 10
mode = 'SH'
log_errors = True


def do_peakfind(fstart, fstop, rbw, psd):
    # find max amplitude
    pamp = max(psd)

    # find what index that max is at
    for i, j in enumerate(psd):
        if j == pamp:
            break

    # calc freq of max value
    pfreq = (i * rbw) + fstart

    # return peak frequency and amplitude
    return (pfreq, pamp)

# open faillog
if log_errors:
    fp = open("mcfail.log", "a")

# connect to siggen
sg = N5183("10.126.110.19")
sg.freq(2400e6)
sg.amplitude(pin)
sg.output(1)

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])
dut.scpiset("*RST")
dut.flush()

# create sweep device
sd = SweepDevice(dut)

# test for a long time
t = 0
while t < numtrials:

    # choose random fstart
    req_fstart = int(random.random() * 8e9)

    # choose random fstop
    req_fstop = req_fstart + int(random.random() * (8e9 - req_fstart))

    # choose random fin between fstart and fstop
    fin = req_fstart + int(random.random() * (req_fstop - req_fstart))

    # choose a random rbw between 3kHz and 500 kHz
    req_rbw = int((random.random() * (500e3 - 3e3)) + 3e3)

    # print test summary
    print "Test #%4d - fstart: %11d, fstop: %11d, rbw: %6d, fin: %11d, mode: %s" % (t, req_fstart, req_fstop, req_rbw, fin, mode), 

    # do test
    sd.logstr = ''
    sd.logtype = 'LOG'
    sg.freq(fin)
    time.sleep(0.250)
    try:
        (act_fstart, act_fstop, psd) = sd.capture_power_spectrum(req_fstart, req_fstop, req_rbw, { }, mode)
    except Exception as detail:
        print sd.logstr
        print "\n\n%s" % detail
        break

    act_rbw = float(act_fstop - act_fstart) / len(psd)
    (pfreq, pamp) = do_peakfind(act_fstart, act_fstop, act_rbw, psd)

    # calculate deltas from expected values
    dfreq = abs(pfreq - fin)
    damp = abs(pamp - pin)

    # test for bad peak
    pass_freq = act_rbw * 2
    if (dfreq > pass_freq) or (damp > pass_amp):
        print ""
        print sd.logstr
        print ""
        print "- FAILED"
        print ""
        print "Test conditions : fstart: %d, fstop: %d, fin: %d, rbw: %d, mode: %s" % (req_fstart, req_fstop, fin, req_rbw, mode), 
        print ""
        print "Results -- fstart: %f, fstop: %f, rbw: %f" % (act_fstart, act_fstop, act_rbw)
        print "Expected (%f, %f), found (%f, %f)" % (fin, pin, pfreq, pamp)
        print "Delta -- freq: %f, amp: %f" % (dfreq, damp)
    
        # log to file?
        if log_errors:
            fp.write("Test conditions : fstart: %d, fstop: %d, fin: %d, rbw: %d, mode: %s\n" % (req_fstart, req_fstop, fin, req_rbw, mode))
            fp.write(" :: results - fstart: %f, fstop: %f, rbw: %f\n" % (act_fstart, act_fstop, act_rbw))
            fp.write(" :: expected (%f, %f), found (%f, %f)\n" % (fin, pin, pfreq, pamp))
            fp.write(" :: delta -- freq: %f, amp: %f\n" % (dfreq, damp))
            fp.write("\n\n")
            fp.flush()

    else:
        # success!
        print "- PASS -- dF: %8.1f, dP: %4.1f" % (dfreq, damp)

    # inc trial count
    t += 1

