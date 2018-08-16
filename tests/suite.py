#!/usr/bin/python

import sys
import time
import unittest
from agilent.devices import N5183
from pyrf.devices.thinkrf import WSA
from pyrf.sweep_device import SweepDevice

global sg
global sd

class TestSweepMethods(unittest.TestCase):

    def do_test(self, fin, req_fstart, req_fstop, req_rbw, mode, save_data = False):
        #self.sd.logtype = 'LOG'
        self.sd.logtype = 'NONE'
        self.sg.freq(fin)
        time.sleep(0.05)

        (act_fstart, act_fstop, psd) = self.sd.capture_power_spectrum(req_fstart, req_fstop, req_rbw, { }, mode)
        act_rbw = float(act_fstop - act_fstart) / len(psd)
        (pfreq, pamp) = self.do_peakfind(act_fstart, act_fstop, act_rbw, psd)

        errmsg = ""

        #errmsg = self.sd.logstr
        #errmsg += "===========================================================================\n"
        #errmsg += "Tested fin: %d, fstart: %d, fstop: %d, rbw: %d, mode: %s\n" % (fin, req_fstart, req_fstop, req_rbw, mode)
        #errmsg += "expected (%f, %f), found (%f, %f)\n" % (fin, -30, pfreq, pamp)
        #errmsg += "delta freq = %f / amp = %f\n" % (abs(pfreq - fin), abs(-30 - pamp))

        # save data
        if save_data:
            self._save_data(fin, req_fstart, req_fstop, req_rbw, mode, act_fstart, act_fstop, act_rbw, psd)

        self.assertAlmostEqual(pamp, -30, delta=10, msg=errmsg)
        self.assertAlmostEqual(pfreq, fin, delta=act_rbw, msg=errmsg)


    def _save_data(self, fin, req_fstart, req_fstop, req_rbw, mode, act_fstart, act_fstop, act_rbw, psd):

            filename = "data-suite-%d-%d-%d-%d-%s.dat" % (req_fstart, req_fstop, int(req_rbw), fin, mode)
            fp = open(filename, "w+")

            fp.write("Requested: fstart/fstop/rbw: %d / %d / %d\n" % (req_start, req_stop, req_rbw))
            fp.write("Actual:    fstart/fstop/rbw: %d / %d / %d\n" % (act_fstart, act_fstop, act_rbw))
            fp.write("\n")

            f = act_fstart
            i = 0
            for d in psd:

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
                f += act_rbw
                i += 1

            fp.write("\n")
            fp.close()

    def do_peakfind(self, fstart, fstop, rbw, psd):
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


    #
    # test cases
    # 

    def test_onestep_01(self):
        self.do_test(105e6, 100e6, 131e6, 3e3, 'SH')
    
    def test_onestep_02(self):
        self.do_test(105e6, 97e6, 131e6, 3e3, 'SH')
    
    def test_onestep_03(self):
        self.do_test(97e6, 97e6, 98e6, 3e3, 'SH')
        
    def test_onestep_04(self):
        self.do_test(7.99e9, 7.98e9, 8e9, 3e3, 'SH')

    def test_onestep_05(self):
        self.do_test(7989091809, 7986970228, 7990416592, 3000, 'SH')
        
    def test_dd_only_01(self):
        self.do_test(37e6, 10e6, 44e6, 3e3, 'SH')
    
    def test_dd_only_02(self):
        self.do_test(37e6, 0, 49e6, 3e3, 'SH')
    
    def test_dd_only_03(self):
        self.do_test(1e6, 9e3, 1.01e6, 3e3, 'SH')
    
    def test_multistep_01(self):
        self.do_test(105e6, 100e6, 207e6, 3e3, 'SH')
    
    def test_multistep_02(self):
        self.do_test(6.9e9, 100e6, 7e9, 3e3, 'SH')
    
    def test_multistep_03(self):
        self.do_test(7.9e9, 100e6, 8e9, 3e3, 'SH')
    
    def test_multistep_04(self):
        self.do_test(7357778397.000000, 7036619837.000000, 7998723745.000000, 3000.000000, 'SH')

    def test_dd_and_sh_01(self):
        self.do_test(37e6, 100e3, 75e6, 3e3, 'SH')
    
    def test_dd_and_sh_02(self):
        self.do_test(74e6, 1e6, 75e6, 3e3, 'SH')
    
    def test_dd_and_sh_03(self):
        self.do_test(7.25e9, 10e6, 7.3e9, 3e3, 'SH')

    def test_misc_01(self):
        self.do_test(3918286871, 882041653, 5759086771, 3e3, 'SH')

    def test_rbw_01(self):
        self.do_test(4.1e9, 100e6, 5e9, 50800, 'SH')

    def test_rbw_02(self):
        self.do_test(7313741145, 6815293986, 7569303377, 500000, 'SH')

    def test_rbw_03(self):
        self.do_test(5208049514, 3720639306, 7296472632, 496814, 'SH') 


# connect to siggen
sg = N5183("10.126.110.19")
sg.freq(2400e6)
sg.amplitude(-30)
sg.output(1)

# connect to wsa
dut = WSA()
dut.connect(sys.argv[1])
dut.scpiset("*RST")
dut.flush()

# create sweep device
sd = SweepDevice(dut)

# pass siggen and sweepdevice to test class
TestSweepMethods.sg = sg
TestSweepMethods.sd = sd

# shift off the IP address
sys.argv = sys.argv[1:]
unittest.main()
