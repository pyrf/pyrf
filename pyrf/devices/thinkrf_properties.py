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

    elif model == 'WSA5000-208':
        p = WSA5000_208Properties()
    elif model == 'WSA5000-108':
        p = WSA5000_108Properties()
    elif model == 'WSA5000-308':
        p = WSA5000_308Properties()
    elif model == 'WSA5000-408':
        p = WSA5000_408Properties()
    elif model == 'WSA5000-408P':
        p = WSA5000_408PProperties()
    elif model == 'WSA5000-427':
        p = WSA5000_427Properties()
    elif model == 'WSA5000-418':
        p = WSA5000_418Properties()
    elif model == 'RTSA7500-8':
        p = BNC_RTSA75008_Properties()
    elif model == 'RTSA7500-8B':
        p = BNC_RTSA75008B_Properties()
    elif model == 'RTSA7500-18':
        p = BNC_RTSA750018_Properties()
    elif model == 'RTSA7500-27':
        p = BNC_RTSA750027_Properties()

    elif model in ['R5500-408', 'RTSA7550-8', 'R5700-408']:
        p = R5500_408Properties()

    elif model in ['R5500-418', 'RTSA7550-18', 'R5700-418']:
        p = R5500_418Properties()

    elif model in ['R5500-427', 'RTSA7550-27', "R6000x-427", 'R5700-427']:
        p = R5500_427Properties()
    else:
        p = WSA5000_220Properties()

    firmware_rev = LooseVersion(firmware.replace('-', '.'))

    # correct for R5500
    if 'R5500' in model or 'RTSA7550' in model or 'R6000x' in model or 'R5700' in model:
        p.REFLEVEL_ERROR = WSA4000Properties.REFLEVEL_ERROR

    return p

def create_sample_size(min, max, multiple):
    start = min
    list = [min]
    curr_spp = min
    while curr_spp < max:
        curr_spp = curr_spp + multiple
        list.append(curr_spp)

    return list


class WSA4000Properties(object):
    model = 'WSA4000'
    manufacturer = 'THINKRF'
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


###
# abstract class for WSA5000 models
#
class WSA5000Properties(WSA4000Properties):
    model = 'WSA5000-BaseClass'
    MINIMUM_FW_VERSION = '3.2.0-rc1'
    TRIGGER_FW_VERSION = '4.1.0'
    REFLEVEL_ERROR = 0
    CAPTURE_FREQ_RANGES = [(50 * M, 8000 * M, IQ)]
    SWEEP_FREQ_RANGE = (100 * M, 8000 * M)
    RFE_ATTENUATION = 20
    RFE_MODES = ('SH', 'SHN', 'ZIF', 'HDR', 'DD', 'IQIN')
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
        'DD': 31.25 * M,
        }
    MAX_TUNABLE = {
        'ZIF': 8000 * M,
        'HDR': 8000 * M,
        'SH': 8000 * M,
        'SHN': 8000 * M,
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
    TUNING_RESOLUTION = 10
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
    DEFAULT_SWEEP_SPAN = 100 * M
    SATURATION_LEVEL = -10.0
    SPECA_DEFAULTS = {
        'mode': 'Sweep SH',
        'center': 2450.0 * M,
        'rbw': 250.0e3,
        'span': DEFAULT_SPECA_SPAN,
        'decimation': 1,
        'fshift': 0.0,
        'device_settings': {
            'attenuator': True,
            'var_attenuator': 17.0,
            'psfm_gain': 'high',
            'iq_output_path': 'DIGITIZER',
            'hdr_gain': 25.0,
            'pll_reference': 'INT',
            'trigger': {'type': 'NONE',
                        'fstart': 2440.0 * M,
                        'fstop': 2460 * M,
                        'amplitude': -100.0},
            },
        'device_class': 'thinkrf.WSA',
        'device_identifier': 'unknown',
        }
    TUNABLE_MODES = ['SH', 'SHN', 'ZIF', 'HDR']
    SPECA_MODES = ['Sweep SH', 'Sweep ZIF', 'Sweep SHN']
    DEFAULT_SPECA_SPAN = MAX_TUNABLE['SHN'] - MIN_TUNABLE['SHN']
    MIN_SPP = 256
    MAX_SPP = 32768
    SPP_MULTIPLE = 32
    MAX_PPB = 14

    # MIN FREQ on the 5000 is restricted to 100kHz
    MIN_FREQ = 100e3

    SAMPLE_SIZES = create_sample_size(MIN_SPP, MAX_SPP * MAX_PPB, SPP_MULTIPLE)
    P1DB_LEVEL = -5
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


###
# properties for a WSA5000-108
#
class WSA5000_108Properties(WSA5000Properties):
    model = 'WSA5000-108'

    # 108 -> limited to SHN, HDR, and DD mode
    RFE_MODES = ('SHN', 'HDR', 'DD')
    SPECA_MODES = ['Sweep SHN']
    SPECA_DEFAULTS = dict(WSA5000Properties.SPECA_DEFAULTS,
        center = 4025 * M,
        mode='Sweep SHN'
    )
    IQ_OUTPUT_CONNECTOR = False


###
# properties for the WSA5000-208
#
class WSA5000_208Properties(WSA5000Properties):
    model = 'WSA5000-208'
    SPECA_DEFAULTS = dict(WSA5000Properties.SPECA_DEFAULTS,
        span = WSA5000Properties.DEFAULT_SPECA_SPAN,
        center = 4025 * M,
    )


###
# properties for a WSA5000-208 v2
#
class WSA5000_208_v2Properties(WSA5000_208Properties):
    model = 'WSA5000-208 v2'


###
# properties class for a WSA5000-220
#
class WSA5000_220Properties(WSA5000Properties):
    model = 'WSA5000-220'

    CAPTURE_FREQ_RANGES = [(50*M, 20000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 20000*M)

    # max frequency is 20 GHz
    MAX_TUNABLE = dict(WSA5000Properties.MAX_TUNABLE, 
            ZIF = 20000 * M, 
            HDR = 20000 * M,
            SH = 20000 * M,
            SHN = 20000 * M,
    )


###
# properties for WSA5000-220 v2
#
class WSA5000_220_v2Properties(WSA5000_220Properties):
    model = 'WSA5000-220 v2'
    # v2 -> hardware revision without SHN mode
    RFE_MODES = ('SH', 'ZIF', 'HDR', 'DD', 'IQIN')


###
# properties for a WSA5000-308
#
class WSA5000_308Properties(WSA5000_108Properties):
    model = 'WSA5000-308'


###
# properties for a WSA5000-408
#
class WSA5000_408Properties(WSA5000Properties):
    model = 'WSA5000-408'
    SATURATION_LEVEL = -10.0

    RFE_MODES = ('SH', 'SHN', 'ZIF', 'HDR', 'DD')

    DEFAULT_SPECA_SPAN = WSA5000Properties.MAX_TUNABLE['SHN'] - WSA5000Properties.MIN_TUNABLE['SHN']
    SPECA_DEFAULTS = dict(WSA5000Properties.SPECA_DEFAULTS,
        span = DEFAULT_SPECA_SPAN,
        center = 4025 * M
    )


###
# properties for WSA5000-418
#
class WSA5000_418Properties(WSA5000_408Properties):
    model = 'WSA5000-418'
    CAPTURE_FREQ_RANGES = [(50*M, 18000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 18000*M)

    # add psfm settings
    SWEEP_SETTINGS = list(WSA5000Properties.SWEEP_SETTINGS) + [ 'var_attenuator', 'psfm_gain' ]
    SWEEP_SETTINGS.remove('attenuator')

    # max frequency is 18 GHz
    MAX_TUNABLE = dict(WSA5000Properties.MAX_TUNABLE, 
            ZIF = 18000 * M, 
            HDR = 18000 * M,
            SH = 18000 * M,
            SHN = 18000 * M,
    )

    DEFAULT_SPECA_SPAN = MAX_TUNABLE['SHN'] - WSA5000Properties.MIN_TUNABLE['SHN']
    SPECA_DEFAULTS = dict(WSA5000Properties.SPECA_DEFAULTS,
        span = DEFAULT_SPECA_SPAN,
        center = 9025 * M
    )


###
# properties for a WSA5000-427
#
class WSA5000_427Properties(WSA5000_418Properties):
    model = 'WSA5000-427'
    CAPTURE_FREQ_RANGES = [(50*M, 27000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 27000*M)
    SATURATION_LEVEL = -17.0

    # max frequency is 27 GHz
    MAX_TUNABLE = dict(WSA5000Properties.MAX_TUNABLE, 
            ZIF = 27000 * M, 
            HDR = 27000 * M,
            SH = 27000 * M,
            SHN = 27000 * M,
    )

    DEFAULT_SPECA_SPAN = MAX_TUNABLE['SHN'] - WSA5000_418Properties.MIN_TUNABLE['SHN']
    SPECA_DEFAULTS = dict(WSA5000_220Properties.SPECA_DEFAULTS,
        span= DEFAULT_SPECA_SPAN,
        center = 13525 * M)


###
# properties for a WSA5000-408P
#
class WSA5000_408PProperties(WSA5000_427Properties):
    model = 'WSA5000-408P'

    CAPTURE_FREQ_RANGES = [(50*M, 8000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 8000*M)
    SATURATION_LEVEL = -10.0

    # max frequency is 8 GHz
    MAX_TUNABLE = dict(WSA5000_427Properties.MAX_TUNABLE, 
            ZIF = 8000 * M, 
            HDR = 8000 * M,
            SH = 8000 * M,
            SHN = 8000 * M,
    )

    DEFAULT_SPECA_SPAN = MAX_TUNABLE['SHN'] - WSA5000_427Properties.MIN_TUNABLE['SHN']
    SPECA_DEFAULTS = dict(WSA5000_427Properties.SPECA_DEFAULTS,
        span = DEFAULT_SPECA_SPAN,
        center = 4000 * M
    )
        

###
# properties for a R5500-408
#
class R5500_408Properties(WSA5000_408Properties):
    model = 'R5500-408'
    MIN_FREQ = 9e3
    RFE_MODES = ('SH', 'ZIF', 'SHN', 'HDR', 'DD')
    SWEEP_SETTINGS = ['rfe_mode', 'fstart', 'fstop', 'fstep', 'fshift',
        'decimation', 'attenuator', 'hdr_gain', 'spp', 'ppb',
        'dwell_s', 'dwell_us',
        'trigtype', 'level_fstart', 'level_fstop', 'level_amplitude']
    DEFAULT_SPECA_SPAN = WSA5000_408Properties.MAX_TUNABLE['SHN']
    SPECA_DEFAULTS = {
        'mode': 'Sweep SH',
        'center': 4000.0 * M,
        'rbw': 250.0e3,
        'span': DEFAULT_SPECA_SPAN,
        'decimation': 1,
        'fshift': 0.0,
        'device_settings': {
            'attenuator': 30.0,
            'var_attenuator': 17.0,
            'psfm_gain': 'high',
            'iq_output_path': 'DIGITIZER',
            'hdr_gain': 25.0,
            'pll_reference': 'INT',
            'trigger': {'type': 'NONE',
                        'fstart': 2440.0 * M,
                        'fstop': 2460 * M,
                        'amplitude': -100.0},
            },
        'device_class': 'thinkrf.WSA',
        'device_identifier': 'unknown',
        }
        

###
# properties for R5500-418
#
class R5500_418Properties(R5500_408Properties):
    model = 'R5500-418'

    CAPTURE_FREQ_RANGES = [(50*M, 18000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 18000*M)

    SWEEP_SETTINGS = list(R5500_408Properties.SWEEP_SETTINGS) + [ 'var_attenuator', 'psfm_gain' ]
    SWEEP_SETTINGS.remove('attenuator')

    # max frequency is 18 GHz
    MAX_TUNABLE = dict(R5500_408Properties.MAX_TUNABLE, 
            ZIF = 18000 * M, 
            HDR = 18000 * M,
            SH = 18000 * M,
            SHN = 18000 * M,
    )
    DEFAULT_SPECA_SPAN = MAX_TUNABLE['SHN']
    SPECA_DEFAULTS = dict(R5500_408Properties.SPECA_DEFAULTS,
        span = DEFAULT_SPECA_SPAN,
        center = 9000 * M,
    )
        
    
###
# properties for R5500-427
#
class R5500_427Properties(R5500_408Properties):
    model = 'R5500-427'
    CAPTURE_FREQ_RANGES = [(50*M, 27000*M, IQ)]
    SWEEP_FREQ_RANGE = (100*M, 27000*M)

    # max frequency is 27 GHz
    MAX_TUNABLE = dict(R5500_408Properties.MAX_TUNABLE, 
            ZIF = 27000 * M, 
            HDR = 27000 * M,
            SH = 27000 * M,
            SHN = 27000 * M,
    )

    DEFAULT_SPECA_SPAN = MAX_TUNABLE['SHN']
    SPECA_DEFAULTS = dict(R5500_408Properties.SPECA_DEFAULTS,
        span = DEFAULT_SPECA_SPAN,
        center = 13500 * M)


###
# properties for BNC whitelabeled devices
#
class BNC_RTSA75008_Properties(WSA5000_408Properties):
    model = 'RTSA7500-8'
    manufacturer = 'Berkley Nucleonics'

class BNC_RTSA75008B_Properties(WSA5000_308Properties):
    model = 'RTSA7500-8B'
    manufacturer = 'Berkley Nucleonics'

class BNC_RTSA750018_Properties(WSA5000_418Properties):
    model = 'RTSA7500-18'
    manufacturer = 'Berkley Nucleonics'

class BNC_RTSA750027_Properties(WSA5000_427Properties):
    model = 'RTSA7500-27'
    manufacturer = 'Berkley Nucleonics'


