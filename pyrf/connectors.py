import socket
from functools import wraps

from pyrf.vrt import Stream
from pyrf import twisted_util

try:
    from twisted.internet import defer
except ImportError:
    defer = None

SCPI_PORT = 37001
VRT_PORT = 37000

def sync_async(f):
    """
    This function decorator turns a generator method in a device class
    like WSA4000
    into a simple method that either blocks until the generator is
    complete, or returns an object for async use, such as a Twisted
    Deferred.

    The behaviour of this function depends on the connector class used
    by the device, stored as self.connector.
    """
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        gen = f(self, *args, **kwargs)
        return self.connector.sync_async(gen)
    return wrapper


class PlainSocketConnector(object):
    """
    This connector makes SCPI/VRT socket connections using plain sockets.
    """

    def connect(self, host):
        self._sock_scpi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_scpi.connect((host, SCPI_PORT))
        self._sock_scpi.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self._sock_vrt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_vrt.connect((host, VRT_PORT))
        self._vrt = Stream(self._sock_vrt)

    def disconnect(self):
        self._sock_scpi.shutdown(socket.SHUT_RDWR)
        self._sock_scpi.close()
        self._sock_vrt.shutdown(socket.SHUT_RDWR)
        self._sock_vrt.close()

    def scpiset(self, cmd):
        self._sock_scpi.send("%s\n" % cmd)

    def scpiget(self, cmd):
        self._sock_scpi.send("%s\n" % cmd)
        buf = self._sock_scpi.recv(1024)
        return buf

    def eof(self):
        return self._vrt.eof

    def has_data(self):
        return self._vrt.has_data()

    def read(self):
        return self._vrt.read_packet()

    def raw_read(self, num):
        return self._sock_vrt.recv(num)

    def has_data(self):
        """
        Check if there is VRT data to read.

        :returns: True if there is a packet to read, False if not
        """
        return self._vrt.has_data()

    def sync_async(self, gen):
        """
        Handler for the @sync_async decorator.  We convert the
        generator to a single return value for simple synchronous use.
        """
        val = None
        try:
            while True:
                val = gen.send(val)
        except StopIteration:
            return val

class TwistedConnector(object):
    """
    A connector that makes SCPI/VRT connections asynchronously using
    Twisted.
    """
    def __init__(self, reactor):
        self._reactor = reactor

    def connect(self, host):
        # this should fail only if twisted is not installed
        from pyrf.twisted_util import HostnameEndpoint

        point = HostnameEndpoint(self._reactor, host, SCPI_PORT)
        d = point.connect(twisted_util.SCPIClientFactory())

        @d.addCallback
        def connect_vrt(scpi):
            self._scpi = scpi
            point = HostnameEndpoint(self._reactor, host, VRT_PORT)
            return point.connect(twisted_util.VRTClientFactory())

        @d.addCallback
        def save_vrt(vrt):
            self._vrt = vrt

        return d

    def disconnect(self):
        pass # FIXME

    def scpiset(self, cmd):
        self._scpi.transport.write("%s\n" % cmd)

    def scpiget(self, cmd):
        self._scpi.transport.write("%s\n" % cmd)
        return self._scpi.expectingLine()

    def sync_async(self, gen):
        def advance(result):
            try:
                d = gen.send(result)
                print d
                d = defer.maybeDeferred(lambda: d)
            except StopIteration:
                print "stopped"
                return
            d.addCallback(advance)
            return d

        return advance(None)

    def eof(self):
        return self._vrt.eof
