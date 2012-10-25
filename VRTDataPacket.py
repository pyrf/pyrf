import struct
import socketread

class VRTDataPacket:
	
	def __init__(self, word, socket):
		self.type = 1
		self.count = (word >> 16) & 0x0f
		self.size = (word >> 0) & 0xffff
		self.data = []

		# read in the rest of the header
		tmpstr = socketread.read(socket, 16)
		if (len(tmpstr) < 16):
			print "error: invalid number of bytes"
			return
		(self.streamId, self.tsi, self.tsf) = struct.unpack(">IIQ", tmpstr)

		# read in the payload
		payloadsize = self.size - 5 - 1
		tmpstr = socketread.read(socket, payloadsize * 4)
		if (len(tmpstr) < (payloadsize * 4)):
			print "error: invalid number of bytes"
			return
	
		# read in data
		for i in range(0, payloadsize * 4, 4):
			self.data.append(struct.unpack(">hh", tmpstr[i:i+4]))

		# read in the trailer
		tmpstr = socketread.read(socket, 4)
		if (len(tmpstr) < 4):
			print "error: invalid number of bytes"
			return

	
	def is_data_packet(self):
		return True


	def is_context_packet(self):
		return False


	def __str__(self):
		return ("Data #%d (%d.%09d) [%d samples]" % (self.count, self.tsi, self.tsf, self.size - 6))
