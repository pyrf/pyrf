import unittest

from pyrf.sweep_device import plan_sweep, SweepStep
from pyrf.devices.thinkrf import WSA4000
from pyrf.units import M


class WSA42(object):
    """
    An imaginary device for testing plan sweep
    """
    FULL_BW = 128*M
    USABLE_BW = 66*M
    MIN_TUNABLE = 96*M
    MAX_TUNABLE = 2044*M
    MIN_DECIMATION = 4
    MAX_DECIMATION = 256
    DECIMATED_USABLE = 0.5
    DC_OFFSET_BW = 2*M

class TestPlanSweep(unittest.TestCase):
    def _plan42(self, start, stop, count, expected, min_points=128,
            max_points=8192, fstart=None, fstop=None):
        """
        Develop a plan for sweeping with a WSA42, verify that
        it matches the expected plan
        """
        rfstart, rfstop, result = plan_sweep(WSA42, start, stop, count,
            min_points=min_points)
        self.assertEquals(result, [SweepStep(*s) for s in expected])
        if fstart is None:
            fstart = start
        if fstop is None:
            fstop = stop
        self.assertEquals(rfstart, fstart)
        self.assertEquals(rfstop, fstop)

    def test_simple_within_sweep_single_exact(self):
        self._plan42(100*M, 132*M, 64,
            [(133*M, 32*M, 0, 1, 256, 62, 64, 64)])

    def test_simple_within_sweep_single_just_inside(self):
        self._plan42(100*M, 131.9*M, 64,
            [(133*M, 32*M, 0, 1, 512, 124, 128, 128)])

    def test_simple_within_sweep_single_just_outside(self):
        self._plan42(100*M, 132.1*M, 64,
            [(133*M, 32*M, 0, 1, 256, 62, 64, 64)])

    def test_simple_within_sweep_double_exact(self):
        self._plan42(100*M, 164*M, 128,
            [(133*M, 32*M, 0, 1, 256, 62, 64, 128)])

    def test_simple_within_sweep_double_points_up(self):
        self._plan42(100*M, 164*M, 129,
            [(133*M, 32*M, 0, 1, 512, 124, 128, 256)])

    def test_simple_within_sweep_double_points_half(self):
        self._plan42(100*M, 164*M, 64,
            [(133*M, 32*M, 0, 1, 128, 31, 32, 64)])

    def test_simple_within_sweep_double_points_min(self):
        self._plan42(100*M, 164*M, 32,
            [(133*M, 32*M, 0, 1, 128, 31, 32, 64)])

    def test_simple_within_sweep_fshift_triple(self):
        self._plan42(100*M, 164*M, 32,
            [(133*M, 30*M, 1*M, 1, 64, 16, 15, 32)],
            min_points=64)

    def test_simple_within_sweep_triple_exact(self):
        self._plan42(100*M, 196*M, 192,
            [(133*M, 32*M, 0, 1, 256, 62, 64, 192)])

    def test_decimated_within_sweep_single_exact(self):
        self._plan42(100*M, 101*M, 4096,
            [(133*M, 1*M, 32.5*M, 64, 8192, 2048, 4096, 4096)])

    def test_decimated_within_sweep_double_exact(self):
        self._plan42(100*M, 102*M, 8192,
            [(133*M, 1*M, 32.5*M, 64, 8192, 2048, 4096, 8192)])

    def test_xxx_truncate_to_left_sweep(self):
        self._plan42(0, 2048*M, 200,
            [(96*M, 32*M, 0, 1, 128, 31, 32, 1952)],
            fstart=63*M, fstop=2043*M)

    #def test_vlow_plus_normal(self):
    #    self._plan4k(30*M, 67*M, 50*K,
    #        [(0, 37187500, 4, 2048, 553, 983, 312),
    #         (90*M, 0, 1, 8192, 655, 1507, 460),])

