import struct
import array
import sys

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
CTX_SWEEPID = (1 << 0)
CTX_STREAMID = (1 << 1)

# values captured in a given frequency range
I_ONLY = 'i_only'
IQ = 'iq'

class InvalidDataReceived(Exception):
    pass


def vrt_packet_reader(raw_read):
    """
    Read a VRT packet, parse it and return an object with its data.

    Implemented as a generator that yields the result of the passed
    raw_read function and accepts the value sent as its data.
    """
    tmpstr = yield raw_read(4)
    (word,) = struct.unpack(">I", tmpstr)
    packet_type = (word >> 28) & 0x0f
    count = (word >> 16) & 0x0f
    size = (word >> 0) & 0xffff

    if packet_type in (VRTCONTEXT, VRTCUSTOMCONTEXT):
        packet_size = (size - 1) * 4
        context_data = yield raw_read(packet_size)
        yield ContextPacket(packet_type, count, size, context_data)

    elif packet_type == VRTDATA:
        data_header = yield raw_read(16)
        stream_id, tsi, tsf = struct.unpack(">IIQ", data_header)
        payload_size = (size - 5 - 1) * 4
        payload = yield raw_read(payload_size)
        trailer = yield raw_read(4)
        yield DataPacket(count, size, stream_id, tsi, tsf, payload)

    else:
        raise InvalidDataReceived("unknown packet type: %s" % packet_type)



class ContextPacket(object):
    """
    A Context Packet received from :meth:`pyrf.devices.thinkrf.WSA4000.read`

    .. attribute:: fields

       a dict containing field names and values from the packet
    """

    def __init__(self, packet_type, count, size, tmpstr):
        self.ptype = packet_type
        self.count = count
        self.size = size
        (self.streamId, self.tsi, self.tsf,indicatorsField,) = struct.unpack(">IIQI", tmpstr[0:20])
        self.fields = {}

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

        if indicators & CTX_SWEEPID:
            (value,) = struct.unpack(">I", data[i:i+4])
            self.fields['sweepid'] = value
            value = "0x%08x" % value
            self.fields['startid'] = value # backwards compat
            i += 4

        elif indicators & CTX_STREAMID:
            (value,) = struct.unpack(">I", data[i:i+4])
            self.fields['streamid'] = value
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
    A Data Packet received from :meth:`pyrf.devices.thinkrf.WSA4000.read`

    .. attribute:: data

       a :class:`pyrf.vrt.IQData` object containing the packet data
    """

    def __init__(self, count, size, streamId, tsi, tsf, payload):
        self.ptype = 1
        self.count = count
        self.size = size
        self.streamId = streamId
        self.tsi = tsi
        self.tsf = tsf

        # interpret data
        self.data = IQData(payload)


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
