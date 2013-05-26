import unittest

from pyrf.sweep_device import plan_sweep
from pyrf.devices.thinkrf import WSA4000
from pyrf.units import M


class WSA42(object):
    """
    An imaginary device for testing plan sweep
    """
    FULL_BW = 128*M
    USABLE_BW = 66*M
    MIN_TUNABLE = 64*M
    MAX_TUNABLE = 2048*M
    MIN_DECIMATION = 2
    MAX_DECIMATION = 256
    DECIMATED_USABLE = 0.75
    DC_OFFSET_BW = 2*M

class TestPlanSweep(unittest.TestCase):
    def _plan42(self, start, stop, count, expected):
        """
        Develop a plan for sweeping with a WSA42, verify that
        it matches the expected plan
        """
        result = plan_sweep(WSA42, start, stop, count, min_points=64)
        self.assertEquals(result, expected)

    def test_simple_within_sweep_single_exact(self):
        self._plan42(100*M, 132*M, 64,
            [(133*M, 149*M, 32*M, 0, 1, 256, 62, 64, 64)])

    def test_simple_within_sweep_single_just_inside(self):
        self._plan42(100*M, 131.9*M, 64,
            [(133*M, 149*M, 32*M, 0, 1, 512, 124, 128, 128)])

    def test_simple_within_sweep_single_just_outside(self):
        self._plan42(100*M, 132.1*M, 64,
            [(133*M, 149*M, 32*M, 0, 1, 256, 62, 64, 64)])

    def test_simple_within_sweep_double_exact(self):
        self._plan42(100*M, 164*M, 128,
            [(133*M, 181*M, 32*M, 0, 1, 256, 62, 64, 128)])



    #def test_vlow_plus_normal(self):
    #    self._plan4k(30*M, 67*M, 50*K,
    #        [(0, 37187500, 4, 2048, 553, 983, 312),
    #         (90*M, 0, 1, 8192, 655, 1507, 460),])

