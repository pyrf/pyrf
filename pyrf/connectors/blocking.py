import socket

from pyrf.connectors.base import sync_async, SCPI_PORT, VRT_PORT

import logging
logger = logging.getLogger(__name__)

class PlainSocketConnector(object):
    """
    This connector makes SCPI/VRT socket connections using plain sockets, of blocking type.
    """

    def connect(self, host):
        self._sock_scpi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_scpi.connect((host, SCPI_PORT))
        self._sock_scpi.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self._sock_vrt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_vrt.connect((host, VRT_PORT))


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

        # send the command
        self._sock_scpi.send(cmd)

        # read the reply (or atleast some of it)
        buf = self._sock_scpi.recv(1024)

        # test the first character to see if this is ascii or block data
        if buf[0] != '#':
            # ascii response, just return it
            logger.debug('scpigot %r', buf)
            return buf

        #
        # first character is '#', so it's block data
        #

        # parse the number of digits
        numlen = int(buf[1])

        # now parse the actual block len
        blocklen = int(buf[2:2 + numlen])

        # figure out how much we have already
        lenread = len(buf) - 2 - numlen

        # read bytes until we get all of it
        blockbuf = buf[2 + numlen:]
        while lenread < blocklen:
            buf = self._sock_scpi.recv(1024)
            blockbuf += buf
            lenread += len(buf)

        # that's all our bytes, return the byte string for them to deal with, but don't return the trailing \n
        return blockbuf[:-1]

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
