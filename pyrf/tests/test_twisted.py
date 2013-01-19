import unittest

from pyrf.twisted_util import VRTClient
from twisted.internet import reactor


class FakeTransport(object):
    disconnecting = False

class TestVRTClient(unittest.TestCase):
    def test_client(self):
        def got_it(d):
            self.assertEquals(d, "hello")

        c = VRTClient()
        c.makeConnection(FakeTransport())
        c.dataReceived("hellohello"*10)
        c.expectingData(5).addCallback(got_it)
        c.expectingData(5).addCallback(got_it)
        c.expectingData(5).addCallback(got_it)
        c.expectingData(5).addCallback(got_it)
        c.expectingData(5).addCallback(got_it)
        c.expectingData(5).addCallback(got_it)


