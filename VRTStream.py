import struct
import socket
import socketread
import VRTContextPacket
import VRTDataPacket

VRTCONTEXT = 4
VRTDATA = 1

class VRTStream:

    def __init__(self, socket):
        self.socket = socket
        self.eof = False

    def has_data(self):
        # read a word
        try:
            tmpstr = socketread.read(self.socket, 4, socket.MSG_DONTWAIT | socket.MSG_PEEK)
        except socket.error:
            self.eof = True
            return False

        return True


    def read_packet(self):
        # read a word
        tmpstr = socketread.read(self.socket, 4, 0)

        # convert to int word
        (word,) = struct.unpack(">I", tmpstr)

        # decode the packet type
        packet_type = (word >> 28) & 0x0f

        if (packet_type == 4):
            return VRTContextPacket.VRTContextPacket(word, self.socket)
        elif (packet_type == 1):
            return VRTDataPacket.VRTDataPacket(word, self.socket)
        else:
            print "error: unknown packet type: %s" % packet_type
            return False
