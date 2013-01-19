try:
    from twisted.internet.protocol import Factory, Protocol
    from twisted.internet import defer
    from twisted.internet.endpoints import TCP4ClientEndpoint
    try: # Twisted >= 13.0 for IPv6 support
        from twisted.internet.endpoints import HostnameEndpoint
    except ImportError:
        from twisted.internet.endpoints import TCP4ClientEndpoint
        HostnameEndpoint = TCP4ClientEndpoint
except ImportError:
    # to allow docstrings to be visible even when twisted
    # imports fail
    Factory = Protocol = StatefulProtocol = object

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class VRTTooMuchData(Exception):
    pass

class VRTClient(Protocol):
    """
    A Twisted protocol for the VRT connection
    """
    TOO_MUCH_UNEXPECTED_DATA = 10**6
    _sful_data = None, 0

    def __init__(self):
        self.eof = False
        self._expected_responses = []

    def makeConnection(self, transport):
        Protocol.makeConnection(self, transport)
        self._sful_data = StringIO(), 0

    def dataReceived(self, data):
        buf, offset = self._sful_data
        buf.seek(0, 2)
        buf.write(data)
        blen = buf.tell() # how many bytes total is in the buffer
        buf.seek(offset)
        while self._expected_responses:
            exp_callback, exp_bytes = self._expected_responses.pop(0)
            if blen - offset < exp_bytes:
                break
            d = buf.read(exp_bytes)
            offset += exp_bytes
            exp_callback(d)

        if self.transport.disconnecting: # XXX: argh stupid hack borrowed right from LineReceiver
            return # dataReceived won't be called again, so who cares about consistent state

        if blen - offset > self.TOO_MUCH_UNEXPECTED_DATA:
            self.transport.loseConnection()
            raise VRTTooMuchData("received too much unexpected data!")

        if offset != 0:
            b = buf.read()
            buf.seek(0)
            buf.truncate()
            buf.write(b)
            offset = 0
        self._sful_data = buf, offset

    def expectingData(self, num_bytes):
        d = defer.Deferred()

        def callback(data):
            print "VRT data: %r" %data
            d.callback(data)
            print "nope"

        self._expected_responses.append((callback, num_bytes))

        self.dataReceived("") # in case enough data is already waiting
        return d

    def connectionLost(self, reason):
        self.eof = True

class VRTClientFactory(Factory):
    def startedConnecting(self, connector):
        pass
    def buildProtocol(self, addr):
        return VRTClient()
    def clientConnectionLost(self, connector, reason):
        pass
    def clientConnectionFailed(self, connector, reason):
        pass

class SCPIClient(Protocol):
    def __init__(self):
        self._expected_responses = []

    def connectionMade(self):
        print "connectionMade"

    def expectingData(self):
        d = defer.Deferred()
        self._expected_responses.append(d)
        return d

    def dataReceived(self, data):
        print "received: %r" % data
        self._expected_responses.pop(0).callback(data)

class SCPIClientFactory(Factory):
    def startedConnecting(self, connector):
        pass
    def buildProtocol(self, addr):
        return SCPIClient()
    def clientConnectionLost(self, connector, reason):
        pass
    def clientConnectionFailed(self, connector, reason):
        pass

