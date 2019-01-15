import socket

from pyrf.connectors.base import sync_async, SCPI_PORT, VRT_PORT

import logging
logger = logging.getLogger(__name__)

class PlainSocketConnector(object):
    """
    This connector makes SCPI/VRT socket connections using plain sockets, of blocking type.
    """

    def __init__(self):
        self._sock_scpi = None
        self._sock_vrt = None

    def connect(self, host, timeout=8): # if after 8s nothing has happened, throw timeout
        """connect scpi and vrt with a timeout"""
        try:
            self._sock_scpi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock_scpi.settimeout(timeout)
            self._sock_scpi.connect((host, SCPI_PORT))
            self._sock_scpi.settimeout(None)
            self._sock_scpi.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        except socket.error as err:
            logger.error('socket connect SCPI failed with %s', err)
            raise
        else:
            try:
                self._sock_vrt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock_vrt.connect((host, VRT_PORT))
            except socket.error as err:
                logger.error('socket connect VRT failed with %s', err)
                self._sock_scpi.shutdown(socket.SHUT_RDWR)
                self._sock_scpi.close()
                raise            

    def disconnect(self):
        self._sock_scpi.shutdown(socket.SHUT_RDWR)
        self._sock_scpi.close()
        self._sock_vrt.shutdown(socket.SHUT_RDWR)
        self._sock_vrt.close()

    def scpiset(self, cmd):
        cmd = "%s\n" % cmd
        logger.debug('scpiset %r', cmd)
        self._sock_scpi.send(cmd)

    def scpiget(self, cmd):
        cmd = "%s\n" % cmd
        logger.debug('scpiset %r', cmd)
        self._sock_scpi.send(cmd)
        buf = self._sock_scpi.recv(1024)
        logger.debug('scpigot %r', buf)
        return buf

    def eof(self):
        # FIXME: lies
        return False

    def has_data(self):
        # FIXME: broken
        return self._vrt.has_data()

    def raw_read(self, num):
        return socketread(self._sock_vrt, num)

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


def socketread(socket, count, flags = None):
    """
    Retry socket read until *count* amount of data received,
    like reading from a file.

    :param int count: the amount of data received
    :param flags: socket.recv() related flags
    """
    if not flags:
        flags = 0
    data = socket.recv(count, flags)
    datalen = len(data)

    if datalen == 0:
        return False

    while datalen < count:
        data = data + socket.recv(count - datalen)
        datalen = len(data)

    return data
