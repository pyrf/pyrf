import unittest

from pyrf.connectors.twisted import VRTClient
from twisted.internet import reactor


class FakeTransport(object):
    disconnecting = False

class TestVRTClient(unittest.TestCase):
    def test_client(self):
        def got_it(d):
            print d
            self.assertEquals(d[:-1], "hello")
            c.expectingData(6).addCallback(got_it)

        c = VRTClient()
        c.makeConnection(FakeTransport())
        c.expectingData(6).addCallback(got_it)
        c.dataReceived(''.join("hello%d" % i for i in range(6)))


