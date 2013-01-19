
try:
    from twisted.internet.protocol import Factory, Protocol
    from twisted.internet import defer
    from twisted.protocols.stateful import StatefulProtocol
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


class VRTTooMuchData(Exception):
    pass

class VRTClient(StatefulProtocol):
    """
    A Twisted protocol for the VRT connection
    """
    TOO_MUCH_UNEXPECTED_DATA = 10**6

    def __init__(self):
        self.eof = False
        self._expected_responses = []

    def getInitialState(self):
        return self._unexpectedInput, self.TOO_MUCH_UNEXPECTED_DATA

    def _unexpectedInput(self, data):
        self.transport.loseConnection()
        raise VRTTooMuchData("received too much unexpected data!")

    def nextExpectedInput(self):
        if not self._expected_responses:
            return self.getInitialState()
        return self._expected_responses.pop(0)

    def expectingData(self, num_bytes):
        d = defer.Deferred()

        def callback(data):
            print "VRT data: %r" %data
            d.callback(data)
            print "nope"
            return self.nextExpectedInput()

        self._expected_responses.append((callback, num_bytes))

        # replace "not expecting anything"
        if self._sful_data[0][0] == self._unexpectedInput:
            ignore, buf, offset = self._sful_data
            self._sful_data = self.nextExpectedInput(), buf, offset
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

