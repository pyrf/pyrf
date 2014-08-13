TRIGGER_TYPE_LEVEL = 'LEVEL'
TRIGGER_TYPE_NONE = 'NONE'

class TriggerSettingsError(Exception):
    pass

class TriggerSettings(object):
    """
    Trigger settings for :meth:`pyrf.devices.thinkrf.WSA.trigger`.

    :param trigtype: "LEVEL" or "NONE" to disable
    :param fstart: starting frequency in Hz
    :param fstop: ending frequency in Hz
    :param amplitude: minumum level for trigger in dBm
    """

    def __init__(self,
            trigtype=TRIGGER_TYPE_NONE,
            fstart=None,
            fstop=None,
            amplitude=None):
        self.trigtype = trigtype
        self.fstart = fstart
        self.fstop = fstop
        self.amplitude = amplitude

    def __str__(self):
        return ("TriggerSettings(%s, %s, %s, %s)" % (self.trigtype, self.fstart, self.fstop, self.amplitude))


class SweepEntry(object):
    """
    Sweep entry for :meth:`pyrf.devices.thinkrf.WSA.sweep_add`

    :param fstart: starting frequency in Hz
    :param fstop: ending frequency in Hz
    :param fstep: frequency step in Hz
    :param fshift: the frequency shift in Hz
    :param decimation: the decimation value (0 or 4 - 1023)
    :param antenna: the antenna (1 or 2)
    :param gain: the RF gain value ('high', 'medium', 'low' or 'vlow')
    :param ifgain: the IF gain in dB (-10 - 34)
    :param hdr_gain: the HDR gain in dB (-10 - 30)
    :param spp: samples per packet
    :param ppb: packets per block
    :param dwell_s: dwell time seconds
    :param dwell_us: dwell time microseconds
    :param trigtype: trigger type ('none', 'pulse' or 'level')
    :param level_fstart: level trigger starting frequency in Hz
    :param level_fstop: level trigger ending frequency in Hz
    :param level_amplitude: level trigger minimum in dBm
    :param attenuator: enable/disable attenuator
    """

    def __init__(self,
            fstart=2400000000,
            fstop=2400000000,
            fstep=100000000,
            fshift=0,
            decimation=0,
            antenna=1,
            gain="vlow",
            ifgain=0,
            hdr_gain=-10,
            spp=1024,
            ppb=1,
            trigtype="none",
            dwell_s=0,
            dwell_us=0,
            level_fstart= 50000000,
            level_fstop=10000000000,
            level_amplitude=-100,
            attenuator=True,
            rfe_mode='ZIF'):
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
        self.dwell_s = dwell_s
        self.dwell_us = dwell_us
        self.trigtype = trigtype
        self.level_fstart = level_fstart
        self.level_fstop = level_fstop
        self.level_amplitude = level_amplitude
        self.attenuator = attenuator
        self.rfe_mode = rfe_mode


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
            + "\tdwell_s: %s\n" % self.dwell_s
            + "\tdwell_us: %s\n" % self.dwell_us
            + "\ttrigtype: %s\n" % self.trigtype
            + "\tlevel:fstart/fstop/famplitude: %d / %d / %d\n" % (self.level_fstart, self.level_fstop, self.level_amplitude)
            + "\tattenuator: %s\n" % self.attenuator
            + "\trfe_mode: %s\n" % self.rfe_mode
            + ")")


