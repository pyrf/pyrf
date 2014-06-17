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
from pyrf.vrt import vrt_packet_reader, generate_speca_packet

import logging
logger = logging.getLogger(__name__)

class TwistedConnectorError(Exception):
    pass

class TwistedConnector(object):
    """
    A connector that makes SCPI/VRT connections asynchronously using
    Twisted.

    A callback may be assigned to vrt_callback that will be called
    with VRT packets as they arrive.  When .vrt_callback is None
    (the default) arriving packets will be ignored.
    """
    def __init__(self, reactor, vrt_callback=None):
        self._reactor = reactor
        self.vrt_callback = vrt_callback

    def connect(self, host, output_file=None):
        point = HostnameEndpoint(self._reactor, host, SCPI_PORT)
        d = point.connect(SCPIClientFactory())

        @d.addCallback
        def connect_vrt(scpi):
            self._scpi = scpi
            point = HostnameEndpoint(self._reactor, host, VRT_PORT)
            return point.connect(VRTClientFactory(self._vrt_callback))

        @d.addCallback
        def save_vrt(vrt):
            self._vrt = vrt

        return d

    def set_recording_output(self, output_file=None):
        self._vrt.set_recording_output(output_file)

    def inject_recording_state(self, state):
        self._vrt.inject_recording_state(state)

    def disconnect(self):
        self._vrt.transport.loseConnection()
        self._scpi.transport.loseConnection()

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
        raise TwistedConnectorError('synchronous read() not supported.')

    def _vrt_callback(self, packet):
        if self.vrt_callback:
            self.vrt_callback(packet)


class VRTClient(Protocol):
    """
    A Twisted protocol for the VRT connection

    :param receive_callback: a function that will be passed a vrt
        DataPacket or ContextPacket when it is received
    """
    _buf = None
    eof = False
    _new_output_file = None
    _output_file = None
    _inject_recording_state = None
    _at_vrt_boundary = True

    def __init__(self, receive_callback):
        self._receive_callback = receive_callback
        self._output_data = []

    def makeConnection(self, transport):
        Protocol.makeConnection(self, transport)
        self._buf = StringIO()
        self._buf_offset = 0
        self._resetReader()
        self._processData()

    def set_recording_output(self, output_file=None):
        if not output_file:
            self._output_file = None
            self._new_output_file = None
            self._output_data = []
        else:
            self._new_output_file = output_file
        if self._at_vrt_boundary:
            self._reached_vrt_boundary()

    def inject_recording_state(self, state):
        self._inject_recording_state = state
        if self._at_vrt_boundary:
            self._reached_vrt_boundary()

    def _reached_vrt_boundary(self):
        """
        In between VRT packets we can record complete vrt packets
        to start new recordings and inject speca state packets
        into recordings.
        """
        if self._output_file and self._output_data:
            for d in self._output_data:
                self._output_file.write(d)
            self._output_data = []

        if self._new_output_file:
            self._output_file = self._new_output_file
            self._new_output_file = None
            self._inject_recording_count = 0

        if self._inject_recording_state and self._output_file:
            data, self._inject_recording_count = generate_speca_packet(
                self._inject_recording_state, self._inject_recording_count)
            self._inject_recording_state = None
            self._output_file.write(data)

    def _resetReader(self):
        self._packet_reader = vrt_packet_reader(self._setBytesRequired)
        next(self._packet_reader)

    def _setBytesRequired(self, x):
        self._bytes_required = x

    def _processData(self):
        """
        If we have received enough bytes process it as VRT data and
        call receive_callback if a complete packet was received.
        """
        while True:
            data = self._bufConsume(self._bytes_required)
            if not data:
                break
            self._at_vrt_boundary = False
            if self._output_file:
                self._output_data.append(data)
            response = self._packet_reader.send(data)
            if response:
                self._at_vrt_boundary = True
                self._reached_vrt_boundary()
                self._receive_callback(response)
                self._resetReader()

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
        self._processData()

    def connectionLost(self, reason):
        self.eof = True

class VRTClientFactory(Factory):
    def __init__(self, receive_callback):
        self._receive_callback = receive_callback

    def startedConnecting(self, connector):
        pass

    def buildProtocol(self, addr):
        return VRTClient(self._receive_callback)

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

