import struct
import socketread

VRTRECEIVER = 0x90000001
VRTDIGITIZER = 0x90000002
VRTCUSTOM = 0x90000004

class VRTContextPacket(object):

    CTX_REFERENCEPOINT = (1 << 30)
    CTX_RFFREQ = (1 << 27)
    CTX_GAIN = (1 << 23)
    CTX_TEMPERATURE = (1 << 18)
    CTX_BANDWIDTH = (1 << 29)
    CTX_RFOFFSET = (1 << 26)
    CTX_REFERENCELEVEL = (1 << 24)
    CTX_STREAMSTART = (1 << 0)

    def __init__(self, pkt_type, word, socket):
        # extract the pieces of word we want
        self.type = pkt_type
        self.count = (word >> 16) & 0x0f
        self.size = (word >> 0) & 0xffff
        self.fields = []

        # now read in the rest of the packet
        packet_size = (self.size - 1) * 4
        tmpstr = socketread.read(socket, packet_size)
        (self.streamId, self.tsi, self.tsf,indicatorsField,) = struct.unpack(">IIQI", tmpstr[0:20])

        # now read all the indicators
        if (self.streamId == 0x90000001):
            self._parseReceiverContext(indicatorsField, tmpstr[20:])
        elif (self.streamId == 0x90000002):
            self._parseDigitizerContext(indicatorsField, tmpstr[20:])
        elif (self.streamId == 0x90000004):
            self._parseCustomContext(indicatorsField, tmpstr[20:])


    def _parseReceiverContext(self, indicators, data):
        i = 0

        if (indicators & self.CTX_REFERENCEPOINT):
            value = struct.unpack(">I", data[i:i+4])
            value = "0x%08x" % value
            self.fields.append(('refpoint', value))
            i += 4

        elif (indicators & self.CTX_RFFREQ):
            (value,) = struct.unpack(">Q", data[i:i+8])
            value = (value >> 20) + ((value & 0x00000000000fffff) / 0x000fffff)
            self.fields.append(('rffreq', value))
            i += 8

        elif (indicators & self.CTX_GAIN):
            (g1,g2) = struct.unpack(">hh", data[i:i+4])
            g1 = (g1 >> 7) + ((g1 & 0x007f) / 0x007f)
            g2 = (g2 >> 7) + ((g2 & 0x007f) / 0x007f)
            self.fields.append(('gain', (g1, g2)))
            i += 4

        elif (indicators & self.CTX_TEMPERATURE):
            (value,) = struct.unpack(">I", data[i:i+4])
            value = (value >> 20) + ((value & 0x00000000000fffff) / 0x000fffff)
            self.fields.append(('temperature', 0))
            i += 4


    def _parseDigitizerContext(self, indicators, data):
        i = 0

        if (indicators & self.CTX_BANDWIDTH):
            (value,) = struct.unpack(">Q", data[i:i+8])
            value = (value >> 20) + ((value & 0x00000000000fffff) / 0x00000000000fffff)
            self.fields.append(('bandwidth', value))
            i += 8

        elif (indicators & self.CTX_RFOFFSET):
            (value,) = struct.unpack(">Q", data[i:i+8])
            value = (value >> 20) + ((value & 0x00000000000fffff) / 0x00000000000fffff)
            self.fields.append(('rfoffset', value))
            i += 8

        elif (indicators & self.CTX_REFERENCELEVEL):
            (value,) = struct.unpack(">h", data[i+2:i+4])
            value = (value >> 7) + ((value & 0x0000007f) / 0x0000007f)
            self.fields.append(('reflevel', value))
            i += 4

        else:
            self.fields.append(('Unknown', ""))


    def _parseCustomContext(self, indicators, data):
        i = 0

        if (indicators & self.CTX_STREAMSTART):
            (value,) = struct.unpack(">I", data[i:i+4])
            value = "0x%08x" % value
            self.fields.append(('startid', value))
            i += 4

        else:
            self.fields.append(('Unknown', ""))


    def is_data_packet(self):
        return False


    def is_context_packet(self, type=None):
        if (type == None):
            return True

        elif (type == "Receiver"):
            return (self.type == VRTRECEIVER)

        elif (type == "Digitizer"):
            return (self.type == VRTDIGITIZER)

        else:
            return False


    def __str__(self):
        return ("Context #%02d [%d.%012d, 0x%08x " % (self.count, self.tsi, self.tsf, self.streamId)) + self.fields.__str__() + "]"
