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
    elif model == 'WSA5000-308':
        p = WSA5000_308Properties()
    elif model == 'WSA5000-408':
        p = WSA5000_408Properties()
    elif model == 'WSA5000-427':
        p = WSA5000_427Properties()
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
        'center': 2450.0 * M,
        'rbw': 122070,
        'span': 125.0 * M,
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
    manufacturer = 'THINKRF'
    MINIMUM_FW_VERSION = '3.2.0-rc1'
    TRIGGER_FW_VERSION = '4.1.0'
    REFLEVEL_ERROR = 0
    CAPTURE_FREQ_RANGES = [(50*M, 20000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 20000*M)
    RFE_ATTENUATION = 20
    RFE_MODES = ('ZIF', 'SH', 'SHN', 'HDR', 'DD', 'IQIN')
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
        'DD': 31.25 * M,
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
        'HDR': 0.50176,
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
    DEFAULT_SPECA_SPAN = 125.0 * M
    SPECA_DEFAULTS = {
        'mode': 'Sweep SH',
        'center': 2450 * M,
        'rbw': 122070.0,
        'span': DEFAULT_SPECA_SPAN,
        'decimation': 1,
        'fshift': 0,
        'device_settings': {
            'attenuator': True,
            'iq_output_path': 'DIGITIZER',
            'hdr_gain': 25.0,
            'pll_reference': 'INT',
            'trigger': {'type': 'NONE',
                        'fstart': 2440.0 * M,
                        'fstop': 2460.0 * M,
                        'amplitude': -100.0},
            },
        'device_class': 'thinkrf.WSA',
        'device_identifier': 'unknown',
        }
    TUNABLE_MODES = ['ZIF', 'SH', 'SHN', 'HDR']
    SPECA_MODES = ['Sweep SH', 'Sweep ZIF']

    MAX_SPP = 32768

    SAMPLE_SIZES = [128, 256, 512, 1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144, 524288]
    DEFAULT_RBW_INDEX = 4
    RBW_VALUES = {}
    for mode in RFE_MODES:
        if DEFAULT_SAMPLE_TYPE[mode] == I_ONLY:
            div = 2
        else:
            div = 1
        rbw_vals = []
        for s in SAMPLE_SIZES:
            # FIXME: this is workaround for SPP limit in the sweep device
            if div == 1 and s == SAMPLE_SIZES[-1]:
                break
            rbw_vals.append((FULL_BW[mode] / s) * div)
        RBW_VALUES[mode] = rbw_vals
    IQ_OUTPUT_CONNECTOR = True

class WSA5000_220_v2Properties(WSA5000_220Properties):
    model = 'WSA5000-220 v2'
    REFLEVEL_ERROR = 0
    # v2 -> hardware revision without SHN mode
    RFE_MODES = ('ZIF', 'SH', 'HDR', 'DD', 'IQIN')

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
    IQ_OUTPUT_CONNECTOR = False

class WSA5000_308Properties(WSA5000_108Properties):
    model = 'WSA5000-308'

class WSA5000_208_v2Properties(WSA5000_220_v2Properties, WSA5000_208Properties):
    model = 'WSA5000-208 v2'

class WSA5000_408Properties(WSA5000_208Properties):
    model = 'WSA5000-408'
    RFE_MODES = ('ZIF', 'SH', 'SHN', 'HDR', 'DD')

class WSA5000_427Properties(WSA5000_220Properties):
    model = 'WSA5000-427'
    # 427 -> increased to 27GHz
    CAPTURE_FREQ_RANGES = [(50*M, 27000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 27000*M)

    MAX_TUNABLE = dict((mode, max(27000*M, f))
        for mode, f in WSA5000_220Properties.MAX_TUNABLE.iteritems())

