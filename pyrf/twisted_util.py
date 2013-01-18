
try:
    from twisted.internet.protocol import Factory, Protocol
    from twisted.internet import defer
    from twisted.protocols.basic import LineOnlyReceiver
    from twisted.internet.endpoints import TCP4ClientEndpoint
    try: # Twisted >= 13.0 for IPv6 support
        from twisted.internet.endpoints import HostnameEndpoint
    except ImportError:
        from twisted.internet.endpoints import TCP4ClientEndpoint
        HostnameEndpoint = TCP4ClientEndpoint
except ImportError:
    # to allow docstrings to be visible even when twisted
    # imports fail
    Factory = Protocol = LineOnlyReceiver = object


class VRTClient(Protocol):
    """
    A Twisted protocol for the VRT connection
    """
    def __init__(self):
        self.eof = False

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

    def expectingLine(self):
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

