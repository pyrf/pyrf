
class WSA4000SweepEntry:

    def __init__(self):
        self.fstart = 2400000000
        self.fstop = 2400000000
        self.fstep = 100000000
        self.fshift = 0
        self.decimation = 0
        self.antenna = 1
        self.gain = "vlow"
        self.ifgain = 0
        self.spp = 1024
        self.ppb = 1
        self.trigtype = "none"
        self.level_fstart =  50000000
        self.level_fstop = 10000000000
        self.level_amplitude = -100

    def __str__(self):
        str = "SweepEntry(\n"
        str = str + "\tfstart: %d\n" % self.fstart
        str = str + "\tfstop: %d\n" % self.fstop
        str = str + "\tfstep: %d\n" % self.fstep
        str = str + "\tfshift: %d\n" % self.fshift
        str = str + "\tdecimation: %d\n" % self.decimation
        str = str + "\tantenna: %d\n" % self.antenna
        str = str + "\tgain: %s\n" % self.gain
        str = str + "\tifgain: %d\n" % self.ifgain
        str = str + "\tspp/ppb: %d/%d\n" % (self.spp, self.ppb)
        str = str + "\ttrigtype: %s\n" % self.trigtype
        str = str + "\tlevel:fstart/fstop/famplitude: %d / %d / %d\n" % (self.level_fstart, self.level_fstop, self.level_amplitude)
        str = str + ")"
        return str

