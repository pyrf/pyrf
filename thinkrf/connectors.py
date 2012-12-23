import socket
from functools import wraps

from thinkrf.vrt import Stream

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
        self._sock_scpi.connect((host, 37001))
        self._sock_scpi.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self._sock_vrt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_vrt.connect((host, 37000))
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
