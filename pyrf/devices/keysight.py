import time
import socket

class N5183:
    def __init__(self, host):
        # setup the socket for talking to the box
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, 5025))
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)

        # setup some initial settings
        self.sweep_start = int(2400e6)
        self.sweep_stop = int(2480e6)
        self.sweep_step = int(100e3)
        self.sweep_dwell = 0.1


    def scpiset(self, scpi):
        self._sock.send("%s\n" % scpi)

    def scpiget(self, scpi):
        self._sock.send("%s\n" % scpi)
        buf = self._sock.recv(1024, 0)
        return buf


    def output(self, state = None):
        if state == None:
            pass
        else:
            self.scpiset(":OUTPUT:STATE %s" % state)


    def amplitude(self, level = None):
        if level == None:
            pass
        else:
            self.scpiset(":POWER %f DBM" % level)


    def freq(self, freq = None):
        if freq == None:
            pass
        else:
            self.scpiset(":FREQ %d Hz" % freq)


    def sweep(self, start=None, stop=None, step=None, dwell=None):
        if start != None:
            self.sweep_start = int(start)

        if stop != None:
            self.sweep_stop = int(stop)

        if step != None:
            self.sweep_step = int(step)

        if dwell != None:
            self.sweep_dwell = dwell

        numpoints = int((self.sweep_stop - self.sweep_start) / self.sweep_step)
        if numpoints > 65535:
            numpoints = 65535

        self.scpiset(":FREQ:START %d" % self.sweep_start)
        self.scpiset(":FREQ:STOP %d" % self.sweep_stop)
        self.scpiset(":SWEEP:POINTS %d" % numpoints)
        self.scpiset(":SWEEP:DWELL %f" % self.sweep_dwell)
        
        # now start the sweep
        self.scpiset(":SOURCE:FREQ:MODE LIST")
        self.scpiset(":INIT:CONT OFF")
        self.scpiset(":TSWEEP")


    def is_busy(self):
        value = self.scpiget("*OPC?")


    def wait(self):
        value = self.scpiset("*WAI")



###
# Agilent 3 Hz to 26.5 GHz Spectrum Analyzer
#
class E4440A:
    def __init__(self, host):
        # setup the socket for talking to the box
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.connect((host, 5025))
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)


    def scpiset(self, scpi):
        self._sock.send("%s\n" % scpi)

    def scpiget(self, scpi):
        self._sock.send("%s\n" % scpi)
        buf = self._sock.recv(1024, 0)
        return buf

    def reset(self):
        self.scpiset("*RST")

    def freq(self, fstart, fstop):
        self.scpiset(":FREQ:START %s" % fstart)
        self.scpiset(":FREQ:STOP %s" % fstop)

    def fcenter(self, freq = None):
        if freq == None:
            pass
        else:
            self.scpiset(":FREQ:CENTER %s" % freq)
    
    def span(self, bw = None):
        if bw == None:
            pass
        else:
            self.scpiset(":FREQ:SPAN %s" % bw)

    def fstop(self, freq = None):
        if freq == None:
            pass
        else:
            self.scpiset(":FREQ:STOP %s" % freq)
    
    def reflevel(self, amp = None, dbperdiv=10):
        if amp == None:
            pass
        else:
            self.scpiset(":display:window:trace:y:rlevel %s dBm" % amp)
            self.scpiset(":display:window:trace:y:pdivision %s dB" % dbperdiv)

    def rbw(self, bw = None):
        if bw == None:
            pass
        elif bw == "auto":
            self.scpiset(":bandwidth:bwidth:auto on")
        else:
            self.scpiset(":bandwidth:bwidth %s" % bw)

    def peakfind(self):
        # have marker1 find the peak
        self.scpiset('CALC:MARK1:MAX')
        freq = scpiget('CALC:MARK1:X?')
        amp = scpiget('CALC:MARK1:Y?')
        return (freq, amp)
    
    def mark_pos(self, marker, xpos = None):
    # set the specified marker to a pos
    
        
            marker_state = self.scpiget('CALC:MARK%d:STATE?' % marker)
            # turn on marker if it is off
            if int(marker_state) == 0:
                self.scpiset('CALC:MARK%d:STATE 1' % marker)
                self.scpiset('CALC:MARK%d:MODE POS' % marker)
            if xpos == None:
                x_pos = self.scpiget('CALC:MARK%d:X?' % marker)
                y_pos = self.scpiget('CALC:MARK%d:Y?' % marker)
                return (float(x_pos), float(y_pos))
            else:
                self.scpiset('CALC:MARK%d:X %f' % (marker, xpos))

    def atten_auto(self, mode = None):
    # set if attenuation should be auto mode ( 'ON', 'OFF')
        if mode == None:
            buff = self.scpiget('POW:ATT:AUTO?')
            return buff
        else:
            self.scpiset('POW:ATT:AUTO %s' % mode)
    
    def cal_mode(self, mode = None):
    # set/get calibration mode ('ON', 'OFF')
        if mode == None:
            buff = self.scpiget('CALIBRATION:AUTO?')
            return buff
        else:
            self.scpiset('CALIBRATION:AUTO %s' % mode)
            
    def trace_mode(self, trace, mode = None):
    # set trace mode (WRITe|MAXHold|MINHold|VIEW|BLANk)
        if mode == None:

            buff = self.scpiget('TRAC%d:MODE?' % trace)
            return buff
        else:
            self.scpiset('TRAC%d:MODE %s' % (trace, mode))
    
    def average_mode(self, mode = None):
    # set/get average mode ('ON', 'OFF')
        if mode == None:
            buff = self.scpiget('AVER?')
            return buff
        else:
            self.scpiset(' %s' % mode)
            