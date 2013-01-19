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
    _buf = None

    def __init__(self):
        self.eof = False
        self._expected_responses = []

    def makeConnection(self, transport):
        Protocol.makeConnection(self, transport)
        self._buf = StringIO()

    def _bufAppend(self, data):
        self._buf.seek(0, 2)
        self._buf.write(data)

    def _bufConsume(self, num_bytes):
        "returns None if not enough bytes available"
        self._buf.seek(0, 2)
        if self._buf.tell() < num_bytes:
            return None
        self._buf.seek(0)
        data = self._buf.read(num_bytes)
        remaining = self._buf.read()
        self._buf.seek(0)
        self._buf.truncate()
        self._buf.write(remaining)
        return data

    def dataReceived(self, data):
        self._bufAppend(data)
        while self._expected_responses:
            data = self._bufConsume(self._expected_responses[0][1])
            if not data:
                break
            callback, num_bytes = self._expected_responses.pop(0)

            callback(data)

    def expectingData(self, num_bytes):
        d = defer.Deferred()

        def callback(data):
            d.callback(data)

        self._expected_responses.append((callback, num_bytes))

        #self.dataReceived("")
        #return d

        data = self._bufConsume(num_bytes)
        if data:
            self._expected_responses.pop(0)
            callback(data)
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
        pass

    def expectingData(self):
        d = defer.Deferred()
        self._expected_responses.append(d)
        return d

    def dataReceived(self, data):
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

