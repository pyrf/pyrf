import struct
import array
import sys

from thinkrf.util import socketread

VRTCONTEXT = 4
VRTCUSTOMCONTEXT = 5
VRTDATA = 1

VRTRECEIVER = 0x90000001
VRTDIGITIZER = 0x90000002
VRTCUSTOM = 0x90000004

CTX_REFERENCEPOINT = (1 << 30)
CTX_RFFREQ = (1 << 27)
CTX_GAIN = (1 << 23)
CTX_TEMPERATURE = (1 << 18)
CTX_BANDWIDTH = (1 << 29)
CTX_RFOFFSET = (1 << 26)
CTX_REFERENCELEVEL = (1 << 24)
CTX_STREAMSTART = (1 << 0)

class InvalidDataReceived(Exception):
    pass


class Stream(object):
    """
    A VRT Packet Stream interface wrapping *socket*.
    """

    def __init__(self, socket):
        self.socket = socket
        self.eof = False

    def has_data(self):
        """
        :returns: True if there is data waiting on *socket*.
        """
        # read a word
        try:
            tmpstr = socketread(self.socket, 4, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        except socket.error:
            self.eof = True
            return False

        return True


    def read_packet(self):
        """
        Read a complete packet from *socket* and return either a
        :class:`thinkrf.vrt.ContextPacket` or a
        :class:`thinkrf.vrt.DataPacket`.
        """
        # read a word
        tmpstr = socketread(self.socket, 4, 0)

        # convert to int word
        (word,) = struct.unpack(">I", tmpstr)

        # decode the packet type
        packet_type = (word >> 28) & 0x0f

        if packet_type in (VRTCONTEXT, VRTCUSTOMCONTEXT):
            return ContextPacket(packet_type, word, self.socket)
        elif packet_type == VRTDATA:
            return DataPacket(word, self.socket)
        else:
            raise InvalidDataReceived("unknown packet type: %s" % packet_type)


class ContextPacket(object):
    """
    A Context Packet received from :meth:`thinkrf.vrt.Stream.read_packet`

    .. attribute:: fields

       a dict containing field names and values from the packet
    """

    def __init__(self, pkt_type, word, socket):
        # extract the pieces of word we want
        self.ptype = pkt_type
        self.count = (word >> 16) & 0x0f
        self.size = (word >> 0) & 0xffff
        self.fields = {}

        # now read in the rest of the packet
        packet_size = (self.size - 1) * 4
        tmpstr = socketread(socket, packet_size)
        (self.streamId, self.tsi, self.tsf,indicatorsField,) = struct.unpack(">IIQI", tmpstr[0:20])

        # now read all the indicators
        if self.streamId == VRTRECEIVER:
            self._parseReceiverContext(indicatorsField, tmpstr[20:])
        elif self.streamId == VRTDIGITIZER:
            self._parseDigitizerContext(indicatorsField, tmpstr[20:])
        elif self.streamId == VRTCUSTOM:
            self._parseCustomContext(indicatorsField, tmpstr[20:])


    def _parseReceiverContext(self, indicators, data):
        i = 0

        if indicators & CTX_REFERENCEPOINT:
            value = struct.unpack(">I", data[i:i+4])
            value = "0x%08x" % value
            self.fields['refpoint'] = value
            i += 4

        elif indicators & CTX_RFFREQ:
            (value,) = struct.unpack(">Q", data[i:i+8])
            value /= 2.0 ** 20
            self.fields['rffreq'] = value
            i += 8

        elif indicators & CTX_GAIN:
            (g1,g2) = struct.unpack(">hh", data[i:i+4])
            g1 /= 2.0 ** 7
            g2 /= 2.0 ** 7
            self.fields['gain'] = (g1, g2)
            i += 4

        elif indicators & CTX_TEMPERATURE:
            (value,) = struct.unpack(">I", data[i:i+4])
            value = value
            self.fields['temperature'] = value
            i += 4

        else:
            self.fields['unknown'] = (indicators, data)

    def _parseDigitizerContext(self, indicators, data):
        i = 0

        if indicators & CTX_BANDWIDTH:
            (value,) = struct.unpack(">Q", data[i:i+8])
            value /= 2.0 ** 20
            self.fields['bandwidth'] = value
            i += 8

        elif indicators & CTX_RFOFFSET:
            (value,) = struct.unpack(">q", data[i:i+8])
            value /= 2.0 ** 20
            self.fields['rfoffset'] = value
            i += 8

        elif indicators & CTX_REFERENCELEVEL:
            (value,) = struct.unpack(">h", data[i+2:i+4])
            value /= 2.0 ** 7
            self.fields['reflevel'] = value
            i += 4

        else:
            self.fields['unknown'] = (indicators, data)


    def _parseCustomContext(self, indicators, data):
        i = 0

        if indicators & CTX_STREAMSTART:
            (value,) = struct.unpack(">I", data[i:i+4])
            value = "0x%08x" % value
            self.fields['startid'] = value
            i += 4

        else:
            self.fields['unknown'] = (indicators, data)


    def is_data_packet(self):
        """
        :returns: False
        """
        return False


    def is_context_packet(self, ptype=None):
        """
        :param ptype: "Receiver", "Digitizer" or None for any packet type

        :returns: True if this packet matches the type passed
        """
        if ptype is None:
            return True

        elif ptype == "Receiver":
            return self.ptype == VRTRECEIVER

        elif ptype == "Digitizer":
            return self.ptype == VRTDIGITIZER

        else:
            return False


    def __str__(self):
        return ("Context #%02d [%d.%012d, 0x%08x " % (
            self.count, self.tsi, self.tsf, self.streamId)
            ) + str(self.fields) + "]"


class IQData(object):
    """
    Data Packet values as a lazy collection of (I, Q) tuples
    read from *binary_data*.

    This object behaves as an immutable python sequence, e.g.
    you may do any of the following:

    .. code-block:: python

       points = len(iq_data)

       i_and_q = iq_data[5]

       for i, q in iq_data:
           print i, q
    """
    def __init__(self, binary_data):
        self._strdata = binary_data
        self._data = None

    def _update_data(self):
        self._data = array.array('h')
        self._data.fromstring(self._strdata)
        if sys.byteorder == 'little':
            self._data.byteswap()

    def __len__(self):
        return len(self._strdata) / 4

    def __getitem__(self, n):
        if not self._data:
            self._update_data()
        return tuple(self._data[n * 2:n * 2 + 2])

    def __iter__(self):
        if not self._data:
            self._update_data()
        for i in range(0, len(self._data), 2):
            yield tuple(self._data[i:i + 2])

    def __reversed__(self):
        if not self._data:
            self._update_data()
        for i in reversed(range(0, len(self._data), 2)):
            yield tuple(self._data[i:i + 2])

    def numpy_array(self):
        """
        Return a numpy array of I, Q values for this data similar to:

        .. code-block:: python

           array([[ -44,    8],
                  [ -40,   60],
                  [ -12,   92],
                  ...,
                  [-132,   -8],
                  [-124,   56],
                  [ -44,   80]], dtype=int16)
        """
        import numpy
        a = numpy.frombuffer(self._strdata, dtype=numpy.int16)
        a = a.newbyteorder('>')
        a.shape = (-1, 2)
        return a


class DataPacket(object):
    """
    A Data Packet received from :meth:`thinkrf.vrt.Stream.read_packet`

    .. attribute:: data

       a :class:`thinkrf.vrt.IQData` object containing the packet data
    """

    def __init__(self, word, socket):
        self.ptype = 1
        self.count = (word >> 16) & 0x0f
        self.size = (word >> 0) & 0xffff

        # read in the rest of the header
        tmpstr = socketread(socket, 16)
        if len(tmpstr) < 16:
            raise InvalidDataReceived("data packet too short: %r" % tmpstr)
        (self.streamId, self.tsi, self.tsf) = struct.unpack(">IIQ", tmpstr)

        # read in the payload
        payloadsize = self.size - 5 - 1
        tmpstr = socketread(socket, payloadsize * 4)
        if (len(tmpstr) < (payloadsize * 4)):
            raise InvalidDataReceived("data packet too short: %r" % tmpstr)

        # interpret data
        self.data = IQData(tmpstr)

        # read in the trailer
        tmpstr = socketread(socket, 4)
        if (len(tmpstr) < 4):
            raise InvalidDataReceived("data packet too short: %r" % tmpstr)


    def is_data_packet(self):
        """
        :returns: True
        """
        return True


    def is_context_packet(self, ptype=None):
        """
        :returns: False
        """
        return False


    def __str__(self):
        return ("Data #%02d [%d.%012d, %d samples]" % (self.count, self.tsi, self.tsf, self.size - 6))
