
class Settings(object):
    pass


class SweepEntry(object):

    def __init__(self,
            fstart=2400000000,
            fstop=2400000000,
            fstep=100000000,
            fshift=0,
            decimation=0,
            antenna=1,
            gain="vlow",
            ifgain=0,
            spp=1024,
            ppb=1,
            trigtype="none",
            level_fstart= 50000000,
            level_fstop=10000000000,
            level_amplitude=-100):
        self.fstart = fstart
        self.fstop = fstop
        self.fstep = fstep
        self.fshift = fshift
        self.decimation = decimation
        self.antenna = antenna
        self.gain = gain
        self.ifgain = ifgain
        self.spp = spp
        self.ppb = ppb
        self.trigtype = trigtype
        self.level_fstart = level_fstart
        self.level_fstop = level_fstop
        self.level_amplitude = level_amplitude


    def __str__(self):
        return ("SweepEntry(\n"
            + "\tfstart: %d\n" % self.fstart
            + "\tfstop: %d\n" % self.fstop
            + "\tfstep: %d\n" % self.fstep
            + "\tfshift: %d\n" % self.fshift
            + "\tdecimation: %d\n" % self.decimation
            + "\tantenna: %d\n" % self.antenna
            + "\tgain: %s\n" % self.gain
            + "\tifgain: %d\n" % self.ifgain
            + "\tspp/ppb: %d/%d\n" % (self.spp, self.ppb)
            + "\ttrigtype: %s\n" % self.trigtype
            + "\tlevel:fstart/fstop/famplitude: %d / %d / %d\n" % (self.level_fstart, self.level_fstop, self.level_amplitude)
            + ")")


