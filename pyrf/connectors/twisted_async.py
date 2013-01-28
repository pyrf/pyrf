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

from pyrf.connectors.base import sync_async, SCPI_PORT, VRT_PORT

import logging
logger = logging.getLogger(__name__)

class TwistedConnector(object):
    """
    A connector that makes SCPI/VRT connections asynchronously using
    Twisted.
    """
    def __init__(self, reactor):
        self._reactor = reactor

    def connect(self, host):
        point = HostnameEndpoint(self._reactor, host, SCPI_PORT)
        d = point.connect(SCPIClientFactory())

        @d.addCallback
        def connect_vrt(scpi):
            self._scpi = scpi
            point = HostnameEndpoint(self._reactor, host, VRT_PORT)
            return point.connect(VRTClientFactory())

        @d.addCallback
        def save_vrt(vrt):
            self._vrt = vrt

        return d

    def disconnect(self):
        pass # FIXME

    def scpiset(self, cmd):
        self._scpi.scpiset("%s\n" % cmd)

    def scpiget(self, cmd):
        return self._scpi.scpiget("%s\n" % cmd)

    def sync_async(self, gen):
        def advance(result):
            try:
                d = gen.send(result)
                d = defer.maybeDeferred(lambda: d)
            except StopIteration:
                return result
            d.addCallback(advance)
            return d

        return advance(None)

    def eof(self):
        return self._vrt.eof

    def raw_read(self, num_bytes):
        return self._vrt.expectingData(num_bytes)


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
        self._buf_offset = 0

    def _bufAppend(self, data):
        if self._buf_offset:
            self._buf.seek(self._buf_offset)
            prefix = self._buf.read()
            self._buf.seek(0)
            self._buf.truncate()
            self._buf.write(prefix)
            self._buf_offset = 0
        self._buf.seek(0, 2)
        self._buf.write(data)

    def _bufConsume(self, num_bytes):
        "returns None if not enough bytes available"
        if self._bufLength() < num_bytes:
            return None
        self._buf.seek(self._buf_offset)
        self._buf_offset += num_bytes
        return self._buf.read(num_bytes)

    def _bufLength(self):
        self._buf.seek(0, 2)
        return self._buf.tell() - self._buf_offset

    def dataReceived(self, data):
        self._bufAppend(data)
        while self._expected_responses:
            data = self._bufConsume(self._expected_responses[0][1])
            if not data:
                break
            callback, num_bytes = self._expected_responses.pop(0)

            callback(data)

        if self._bufLength() > self.TOO_MUCH_UNEXPECTED_DATA:
            self.transport.loseConnection()
            raise VRTTooMuchData("Too much unexpected data received")

    def expectingData(self, num_bytes):
        d = defer.Deferred()

        data = self._bufConsume(num_bytes)
        if data:
            d.callback(data)
        else:
            self._expected_responses.append((d.callback, num_bytes))
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
    _pending = None

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)

    def scpiset(self, cmd):
        if self._pending:
            # prevent reordering
            self._pending.append((cmd, None))
        else:
            logger.debug('scpiset %r', cmd)
            self.transport.write(cmd)

    def scpiget(self, cmd):
        d = defer.Deferred()
        if self._pending:
            # command pipelining not supported
            self._pending.append((cmd, d))
        else:
            self._pending = [('', d)]
            self.transport.write(cmd)
            logger.debug('scpiget %r', cmd)
        return d

    def dataReceived(self, data):
        cmd, d = self._pending.pop(0)
        logger.debug('scpigot %r', data)
        if d:
            d.callback(data)

        while self._pending:
            cmd, d = self._pending[0]
            logger.debug('scpi(%s) %r', 'get' if d else 'set', cmd)
            self.transport.write(cmd)
            if d:
                break
            self._pending.pop(0)


class SCPIClientFactory(Factory):
    def startedConnecting(self, connector):
        pass
    def buildProtocol(self, addr):
        return SCPIClient()
    def clientConnectionLost(self, connector, reason):
        pass
    def clientConnectionFailed(self, connector, reason):
        pass

