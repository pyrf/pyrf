TRIGGER_TYPE_LEVEL = 'LEVEL'
TRIGGER_TYPE_NONE = 'NONE'

class TriggerSettingsError(Exception):
    """
    Exception for the trigger settings to state an error() has occured
    """
    pass

class TriggerSettings(object):
    """
    Trigger settings for :meth:`pyrf.devices.thinkrf.WSA.trigger`.

    :param str trigtype: "LEVEL", "PULSE", or "NONE" to disable
    :param int fstart: trigger starting frequency in Hz
    :param int fstop: trigger ending frequency in Hz
    :param float amplitude: minimum level for trigger in dBm

    :return: a string in the format: TriggerSettings(trigger type, fstart, fstop, amplitude)
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
    Sweep entry setup for :meth:`pyrf.devices.thinkrf.WSA.sweep_add`

    :param int fstart: starting frequency in Hz
    :param int fstop: ending frequency in Hz
    :param int fstep: frequency step in Hz
    :param int fshift: the frequency shift in Hz
    :param int decimation: the decimation value (0 or 4 - 1023)
    :param str gain: the RF gain value ('high', 'medium', 'low' or 'vlow')
    :param int ifgain: the IF gain in dB (-10 - 34)

        .. note:: parameter is deprecated, kept for a legacy device

    :param int hdr_gain: the HDR gain in dB (-10 - 30)
    :param int spp: samples per packet (256 - max, a multiple of 32) that fit in one VRT packet
    :param int ppb: data packets per block
    :param int dwell_s: dwell time seconds
    :param int dwell_us: dwell time microseconds
    :param str trigtype: trigger type ('none', 'pulse' or 'level')
    :param int level_fstart: level trigger starting frequency in Hz
    :param int level_fstop: level trigger ending frequency in Hz
    :param float level_amplitude: level trigger minimum in dBm
    :param attenuator: vary depending on the product
    :param str rfe_mode: RFE mode to be used, such as 'SH', 'SHN', 'DD', etc.

    :return: a string list of the sweep entry's settings
    """

    def __init__(self,
            fstart=2400000000,
            fstop=2400000000,
            fstep=100000000,
            fshift=0,
            decimation=0,
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
            attenuator=30,
            rfe_mode='SH'):

        self.fstart = fstart
        self.fstop = fstop
        self.fstep = fstep
        self.fshift = fshift
        self.decimation = decimation
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
