import unittest

from pyrf.sweep_device import SweepPlanner, sweepSettings
from pyrf.units import M


class virtualWSA(object):
    """
    An imaginary device for testing plan sweep
    """

    class properties(object):
        RFE_MODES = ('SH')

        FULL_BW = {'SH':128*M}
        USABLE_BW = {'SH':40*M}
        MIN_TUNABLE = {'SH':50*M}
        MAX_TUNABLE = {'SH':8000*M}
        MIN_DECIMATION = {'SH':4}
        MAX_DECIMATION = {'SH':256}

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
        SWEEP_SETTINGS = ['rfe_mode', 'fstart', 'fstop', 'fstep', 'fshift',
            'decimation', 'attenuator', 'hdr_gain', 'spp', 'ppb',
            'dwell_s', 'dwell_us',
            'trigtype', 'level_fstart', 'level_fstop', 'level_amplitude']

        DECIMATED_USABLE = 0.5
        DC_OFFSET_BW = 2*M
        TUNING_RESOLUTION = 10

class TestPlanSweep(unittest.TestCase):
    def _plan_virtual_sweep(self, start, stop, rbw, expected_settings, min_points=128,
            max_points=8192, fstart=None, fstop=None):
        """
        Develop a plan for sweeping with a virtualWSA, verify that
        it matches the expected plan
        """
        sweep_panner = SweepPlanner(virtualWSA.properties)
        sweep_settings = sweep_panner.plan_sweep(
        start,
        stop,
        rbw,
        mode='SH')

        # check expected spectral points
        expected_points = int((stop - start) / rbw)
        self.assertEquals(sweep_settings.spectral_points, expected_points)

        # calculated if DD mode was expected
        if start < virtualWSA.properties.MIN_TUNABLE['SH']:
            dd = True
        else:
            dd = False

        self.assertEquals(sweep_settings.dd_mode, dd)
        print sweep_settings.fstart, sweep_settings.fstop
    def test_simple_single_exact(self):
        """
        [xxxxxx(64 bins)xxxxxxxxxxxxxxx]
        ^100M     ^110M     ^120M     ^130M
        """
        expected_settings = sweepSettings()
        expected_settings.fstart = 50 * M
        expected_settings.fstop = 200 * M
        
        self._plan_virtual_sweep(50*M, 200*M, 500000, expected_settings.fstart)

    # def test_simple_single_just_inside(self):
    #     """
    #     [xxxxx(128 bins)xxxxxxxxxxxxxxx] <- 131.9M
    #     ^100M     ^110M     ^120M     ^130M
    #     """
    #     self._plan_virtual_sweep(100*M, 131.9*M, 500000)

    # def test_simple_single_just_outside(self):
    #     """
    #     [xxxxx(64 bins)xxxxxxxxxxxxxxxx] <- 130.1M
    #     ^100M     ^110M     ^120M     ^130M
    #     """
    #     self._plan_virtual_sweep(100*M, 132.1*M, 501000)

    # def test_simple_double_exact(self):
    #     """
    #     [xxxxxxx(64 bins)xxxxxxxxxxxxxx][xxxxxxx(64 bins)xxxxxxxxxxxxxx]
    #     ^100M     ^110M     ^120M     ^130M     ^140M     ^150M     ^160M
    #     """
    #     self._plan_virtual_sweep(100*M, 164*M, 500000)

    # def test_simple_double_points_up(self):
    #     """
    #     [xxxxxxx(128 bins)xxxxxxxxxxxxx][xxxxxxx(128 bins)xxxxxxxxxxxxx]
    #     ^100M     ^110M     ^120M     ^130M     ^140M     ^150M     ^160M
    #     """
    #     self._plan_virtual_sweep(100*M, 164*M, 496000)

    # def test_simple_double_points_half(self):
    #     """
    #     [xxxxxxx(32 bins)xxxxxxxxxxxxxx][xxxxxxxx(32 bins)xxxxxxxxxxxxx]
    #     ^100M     ^110M     ^120M     ^130M     ^140M     ^150M     ^160M
    #     """
    #     self._plan_virtual_sweep(100*M, 164*M, 1*M)

    # def test_simple_double_points_min(self):
    #     """
    #     [xxxxxxx(32 bins)xxxxxxxxxxxxxx][xxxxxxxx(32 bins)xxxxxxxxxxxxx]
    #     ^100M     ^110M     ^120M     ^130M     ^140M     ^150M     ^160M
    #     """
    #     self._plan_virtual_sweep(100*M, 164*M, 2*M)

    # def test_simple_triple_exact(self):
    #     """
    #     [x(64 bins)xxxx][x(64 bins)xxxx][x(64 bins)xxxx]
    #     ^100M     ^120M     ^140M     ^160M     ^180M
    #     """
    #     self._plan_virtual_sweep(100*M, 196*M, 500000)

    # def test_truncate_to_left_sweep(self):
    #     """
    #     [x(32 bins)xxxx] ... [x(32 bins)xxxx]
    #     ^63M                                 ^1983M
    #     """
    #     self._plan_virtual_sweep(0, 2048*M, 1024000)

    # def test_empty_range(self):
    #     self._plan_virtual_sweep(2400*M, 2400*M, 500)

    # def test_invalid_range(self):
    #     self._plan_virtual_sweep(2400*M, 2300*M, 500)


