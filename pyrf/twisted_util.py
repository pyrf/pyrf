
try:
    from twisted.internet.protocol import Factory, Protocol
    from twisted.internet.endpoints import TCP4ClientEndpoint
    try: # Twisted >= 13.0 for IPv6 support
        from twisted.internet.endpoints import HostnameEndpoint
    except ImportError:
        from twisted.internet.endpoints import TCP4ClientEndpoint
        HostnameEndpoint = TCP4ClientEndpoint
except ImportError:
    # to allow docstrings to be visible even when twisted
    # imports fail
    Factory = Protocol = object


class VRTClient(Protocol):
    """
    A Twisted protocol for the VRT connection
    """
    pass

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
    def connectionMade(self):
        print "connectionMade"
        self.transport.write(":*idn?\n")

    def dataReceived(self, data):
        print "received: %r" % data
        reactor.stop()

class SCPIClientFactory(Factory):
    def startedConnecting(self, connector):
        pass
    def buildProtocol(self, addr):
        return SCPIClient()
    def clientConnectionLost(self, connector, reason):
        pass
    def clientConnectionFailed(self, connector, reason):
        pass

