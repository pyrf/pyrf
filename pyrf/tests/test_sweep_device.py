import unittest

from pyrf.sweep_device import plan_sweep, SweepStep
from pyrf.units import M


class WSA42(object):
    """
    An imaginary device for testing plan sweep
    """

    class properties(object):
        FULL_BW = 128*M
        USABLE_BW = 66*M
        MIN_TUNABLE = 96*M
        MAX_TUNABLE = 2044*M
        MIN_DECIMATION = 4
        MAX_DECIMATION = 256
        DECIMATED_USABLE = 0.5
        DC_OFFSET_BW = 2*M
        TUNING_RESOLUTION = 100000

class TestPlanSweep(unittest.TestCase):
    def _plan42(self, start, stop, rbw, expected, min_points=128,
            max_points=8192, fstart=None, fstop=None):
        """
        Develop a plan for sweeping with a WSA42, verify that
        it matches the expected plan
        """
        rfstart, rfstop, result = plan_sweep(WSA42, start, stop, rbw,
            min_points=min_points)
        self.assertEquals(result, [SweepStep(*s) for s in expected])
        if fstart is None:
            fstart = start
        if fstop is None:
            fstop = stop
        self.assertEquals(rfstart, fstart)
        self.assertEquals(rfstop, fstop)

    def test_simple_single_exact(self):
        """
        [xxxxxx(64 bins)xxxxxxxxxxxxxxx]
        ^100M     ^110M     ^120M     ^130M
        """
        self._plan42(100*M, 132*M, 500000,
            [(133*M, 32*M, 0, 1, 256, 62, 64, 0, 64)])

    def test_simple_single_just_inside(self):
        """
        [xxxxx(128 bins)xxxxxxxxxxxxxxx] <- 131.9M
        ^100M     ^110M     ^120M     ^130M
        """
        self._plan42(100*M, 131.9*M, 496000,
            [(133*M, 32*M, 0, 1, 512, 124, 128, 0, 128)],
            fstop=132*M)

    def test_simple_single_just_outside(self):
        """
        [xxxxx(64 bins)xxxxxxxxxxxxxxxx] <- 130.1M
        ^100M     ^110M     ^120M     ^130M
        """
        self._plan42(100*M, 132.1*M, 501000,
            [(133*M, 32*M, 0, 1, 256, 62, 64, 0, 64)],
            fstop=132*M)

    def test_simple_double_exact(self):
        """
        [xxxxxxx(64 bins)xxxxxxxxxxxxxx][xxxxxxx(64 bins)xxxxxxxxxxxxxx]
        ^100M     ^110M     ^120M     ^130M     ^140M     ^150M     ^160M
        """
        self._plan42(100*M, 164*M, 500000,
            [(133*M, 32*M, 0, 1, 256, 62, 64, 0, 128)])

    def test_simple_double_points_up(self):
        """
        [xxxxxxx(128 bins)xxxxxxxxxxxxx][xxxxxxx(128 bins)xxxxxxxxxxxxx]
        ^100M     ^110M     ^120M     ^130M     ^140M     ^150M     ^160M
        """
        self._plan42(100*M, 164*M, 496000,
            [(133*M, 32*M, 0, 1, 512, 124, 128, 0, 256)])

    def test_simple_double_points_half(self):
        """
        [xxxxxxx(32 bins)xxxxxxxxxxxxxx][xxxxxxxx(32 bins)xxxxxxxxxxxxx]
        ^100M     ^110M     ^120M     ^130M     ^140M     ^150M     ^160M
        """
        self._plan42(100*M, 164*M, 1*M,
            [(133*M, 32*M, 0, 1, 128, 31, 32, 0, 64)])

    def test_simple_double_points_min(self):
        """
        [xxxxxxx(32 bins)xxxxxxxxxxxxxx][xxxxxxxx(32 bins)xxxxxxxxxxxxx]
        ^100M     ^110M     ^120M     ^130M     ^140M     ^150M     ^160M
        """
        self._plan42(100*M, 164*M, 2*M,
            [(133*M, 32*M, 0, 1, 128, 31, 32, 0, 64)])

    def test_simple_triple_exact(self):
        """
        [x(64 bins)xxxx][x(64 bins)xxxx][x(64 bins)xxxx]
        ^100M     ^120M     ^140M     ^160M     ^180M
        """
        self._plan42(100*M, 196*M, 500000,
            [(133*M, 32*M, 0, 1, 256, 62, 64, 0, 192)])

    def test_decimated_single_exact(self):
        """
        [x(4096 bins)xx]
        ^100M           ^101M
        """
        self._plan42(100*M, 101*M, 245,
            [(133*M, 1*M, 32.5*M, 64, 8192, 2048, 4096, 0, 4096)])

    def test_decimated_double_exact(self):
        """
        [x(4096 bins)xx][x(4096 bins)xx]
        ^100M           ^101M           ^102M
        """
        self._plan42(100*M, 102*M, 245,
            [(133*M, 1*M, 32.5*M, 64, 8192, 2048, 4096, 0, 8192)])

    def test_truncate_to_left_sweep(self):
        """
        [x(32 bins)xxxx] ... [x(32 bins)xxxx]
        ^63M                                 ^1983M
        """
        self._plan42(0, 2048*M, 1024000,
            [(96*M, 32*M, 0, 1, 128, 31, 32, 0, 1920)],
            fstart=63*M, fstop=1983*M)

    def test_empty_range(self):
        self._plan42(2400*M, 2400*M, 500, [])

    def test_invalid_range(self):
        self._plan42(2400*M, 2300*M, 500, [],
            fstop=2400*M)

    #def test_vlow_plus_normal(self):
    #    self._plan4k(30*M, 67*M, 50*K,
    #        [(0, 37187500, 4, 2048, 553, 983, 312),
    #         (90*M, 0, 1, 8192, 655, 1507, 460),])


