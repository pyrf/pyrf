import unittest

from pyrf.sweep_device import plan_sweep
from pyrf.devices.thinkrf import WSA4000

M = 10**6
K = 10**3

class TestPlanSweep(unittest.TestCase):
    def _plan4k(self, start, stop, bin_size, expected):
        """
        Develop a plan for sweeping with a WSA4000, verify that
        it matches the expected plan
        """
        result = plan_sweep(WSA4000, start, stop, bin_size)
        self.assertEquals(result, expected)

    def test_within_normal_sweep(self):
        self._plan4k(2400*M, 5000*M, 10*M, 

    def test_vlow(self):
        pass

    def test_vlow_plus_normal(self):
        self._plan4k(30*M, 67*M, 50*K,
            [(0, 37187500, 4, 2048, 553, 983, 312),
             (90*M, 0, 1, 8192, 655, 1507, 460),])

    def test_full_range(self):
        pass
