from distutils.version import StrictVersion, LooseVersion

from pyrf.units import M
from pyrf.vrt import I_ONLY, IQ


def wsa_properties(device_id):
    """
    Return a WSA*Properties class for device_id passed
    """
    mfr, model_rev, serial, firmware = device_id.split(',')
    model, _space, rev = model_rev.partition(' ')
    if model == 'WSA4000':
        return WSA4000Properties()

    # revision numbers jumped backwards when switching to major.minor
    rev = rev.lstrip('v')
    if '.' in rev:
        old_v2 = StrictVersion(rev) < StrictVersion('1.2')
    else:
        old_v2 = int(rev) < 3

    if model == 'WSA5000-220' and old_v2:
        p = WSA5000_220_v2Properties()
    elif model == 'WSA5000-208' and old_v2:
        p = WSA5000_208_v2Properties()
    elif model == 'WSA5000-208':
        p = WSA5000_208Properties()
    elif model == 'WSA5000-108':
        p = WSA5000_108Properties()
    else:
        p = WSA5000_220Properties()

    firmware_rev = LooseVersion(firmware.replace('-', '.'))
    # correct for old reflevels
    if '.' not in rev or firmware_rev < LooseVersion('4.2'):
        p.REFLEVEL_ERROR = WSA4000Properties.REFLEVEL_ERROR

    if firmware_rev < LooseVersion(p.TRIGGER_FW_VERSION):
        p.LEVEL_TRIGGER_RFE_MODES = []
    return p

class WSA4000Properties(object):
    model = 'WSA4000'
    REFLEVEL_ERROR = 15.7678
    CAPTURE_FREQ_RANGES = [(0, 40*M, I_ONLY), (90*M, 10000*M, IQ)]
    SWEEP_FREQ_RANGE = (90*M, 10000*M)

    RFE_MODES = ('ZIF',)

    DEFAULT_SAMPLE_TYPE = {'ZIF': IQ} # almost true, see CAPTURE_FREQ_RANGES
    FULL_BW = {'ZIF': 125*M}
    USABLE_BW = {'ZIF': 90*M}
    MIN_TUNABLE = {'ZIF': 90*M}
    MAX_TUNABLE = {'ZIF': 10000*M}
    MIN_DECIMATION = {'ZIF': 4}
    MAX_DECIMATION = {'ZIF': 1023}
    DECIMATED_USABLE = 0.5
    PASS_BAND_CENTER = {'ZIF': 0.5}
    DC_OFFSET_BW = 240000 # XXX: an educated guess
    TUNING_RESOLUTION = 100000
    FSHIFT_AVAILABLE = {'ZIF': True}
    SWEEP_SETTINGS = ['fstart', 'fstop', 'fstep', 'fshift', 'decimation',
        'antenna', 'gain', 'ifgain', 'spp', 'ppb', 'dwell_s', 'dwell_us',
        'trigtype', 'level_fstart', 'level_fstop', 'level_amplitude']

    SPECA_DEFAULTS = {
        'mode': 'ZIF',
        'center': 2450 * M,
        'rbw': 122070,
        'span': 125 * M,
        'decimation': 1,
        'fshift': 0,
        'device_settings': {
            'antenna': 1,
            'ifgain': 0,
            'gain': 'low',
            },
        'device_class': 'thinkrf.WSA',
        'device_identifier': 'unknown',
        }
    SPECA_MODES = ['Sweep ZIF']


class WSA5000_220Properties(object):
    model = 'WSA5000-220'
    MINIMUM_FW_VERSION = '3.2.0-rc1'
    TRIGGER_FW_VERSION = '4.1.0'
    REFLEVEL_ERROR = 0
    CAPTURE_FREQ_RANGES = [(50*M, 20000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 20000*M)
    RFE_ATTENUATION = 20
    RFE_MODES = ('ZIF', 'SH', 'SHN', 'HDR', 'IQIN', 'DD')
    DEFAULT_SAMPLE_TYPE = {
        'ZIF': IQ,
        'SH': I_ONLY,
        'SHN': I_ONLY,
        'HDR': I_ONLY,
        'IQIN': IQ,
        'DD': I_ONLY,
        }
    FULL_BW = {
        'ZIF': 125 * M,
        'HDR': 0.16276 * M,
        'SH': 62.5 * M,
        'SHN': 62.5 * M,
        'DEC_SH': 125 * M,
        'DEC_SHN': 125 * M,
        'IQIN': 125 * M,
        'DD': 62.5 * M,
        }
    USABLE_BW = {
        'ZIF': 100 * M,
        'HDR': 0.1 * M,
        'SH': 40 * M,
        'SHN': 10 * M,
        'DEC_SH': 100 * M,
        'DEC_SHN': 100 * M,
        'IQIN': 100 * M,
        'DD': 62.5 * M,
        }
    MIN_TUNABLE = {
        'ZIF': 50 * M,
        'HDR': 50 * M,
        'SH': 50 * M,
        'SHN': 50 * M,
        'IQIN': 0,
        'DD': 31.24 * M,
        }
    MAX_TUNABLE = {
        'ZIF': 20000 * M,
        'HDR': 20000 * M,
        'SH': 20000 * M,
        'SHN': 20000 * M,
        'IQIN': 0,
        'DD': 31.24 * M,
        }
    MIN_DECIMATION = {
        'ZIF': 4,
        'HDR': None,
        'SH': 4,
        'SHN': 4,
        'IQIN': 4,
        'DD': 4,
        }
    MAX_DECIMATION = {
        'ZIF': 1024,
        'HDR': None,
        'SH': 4,
        'SHN': 4,
        'IQIN': 1024,
        'DD': 1024,
        }
    DECIMATED_USABLE = 0.80
    PASS_BAND_CENTER = {
        'ZIF': 0.5,
        'HDR': 0.6,
        'SH': 0.56,
        'SHN': 0.56,
        'DEC_SH': 0.5,
        'DEC_SHN': 0.5,
        'IQIN': 0.5,
        'DD': 0.5,
        }
    DC_OFFSET_BW = 240000 # XXX: an educated guess
    TUNING_RESOLUTION = 100000
    FSHIFT_AVAILABLE = {
        'ZIF': True,
        'HDR': False,
        'SH': True,
        'SHN': True,
        'IQIN': True,
        'DD': True,
        }
    SWEEP_SETTINGS = ['rfe_mode', 'fstart', 'fstop', 'fstep', 'fshift',
        'decimation', 'attenuator', 'hdr_gain', 'spp', 'ppb',
        'dwell_s', 'dwell_us',
        'trigtype', 'level_fstart', 'level_fstop', 'level_amplitude']

    LEVEL_TRIGGER_RFE_MODES = ['SH', 'SHN', 'ZIF']

    SPECA_DEFAULTS = {
        'mode': 'Sweep SH',
        'center': 2450 * M,
        'rbw': 122070,
        'span': 125 * M,
        'decimation': 1,
        'fshift': 0,
        'device_settings': {
            'attenuator': True,
            'iq_output_path': 'DIGITIZER',
            'hdr_gain': -10,
            'pll_reference': 'INT',
            'trigger': {'type': 'NONE',
                        'fstart': 2440 * M,
                        'fstop': 2460 * M,
                        'amplitude': -110},
            },
        'device_class': 'thinkrf.WSA',
        'device_identifier': 'unknown',
        }
    SPECA_MODES = ['Sweep SH', 'Sweep ZIF']


class WSA5000_220_v2Properties(WSA5000_220Properties):
    model = 'WSA5000-220 v2'
    REFLEVEL_ERROR = 0
    # v2 -> hardware revision without SHN mode
    RFE_MODES = ('ZIF', 'SH', 'HDR', 'IQIN', 'DD')


class WSA5000_208Properties(WSA5000_220Properties):
    model = 'WSA5000-208'
    # 208 -> limited to 8GHz

    MAX_TUNABLE = dict((mode, min(8000*M, f))
        for mode, f in WSA5000_220Properties.MAX_TUNABLE.iteritems())

class WSA5000_108Properties(WSA5000_208Properties):
    model = 'WSA5000-108'
    # 108 -> limited to SHN, HDR, and DD mode
    RFE_MODES = ('SHN', 'HDR', 'DD')
    SPECA_MODES = []
    SPECA_DEFAULTS = dict(WSA5000_208Properties.SPECA_DEFAULTS,
        mode='SHN')

class WSA5000_208_v2Properties(WSA5000_220_v2Properties, WSA5000_208Properties):
    model = 'WSA5000-208 v2'


