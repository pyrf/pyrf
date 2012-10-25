import socket
from collections import namedtuple
import VRTStream
import WSA4000SweepEntry

class WSA4000:

	def __init__(self):
		self.sock = namedtuple('socket', ['scpi', 'vrt'])


	## connects to a wsa
	#
	# @param host - the hostname or IP to connect to
	def connect(self, host):
		self.sock.scpi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.scpi.connect((host, 37001))
		self.sock.scpi.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
		self.sock.vrt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.sock.vrt.connect((host, 37000))
		self.vrt = VRTStream.VRTStream(self.sock.vrt);


	## send a scpi command
	#
	# @param cmd - the command to send
	def scpiset(self, cmd):
		self.sock.scpi.send("%s\n" % cmd)


	## get a scpi command
	#
	# @param cmd - the command to send
	# @return - the response back from the box if any
	def scpiget(self, cmd):
		self.sock.scpi.send("%s\n" % cmd)
		buf = self.sock.scpi.recv(1024)
		return buf


	## get the box identification string
	#
	# @return - the id string
	def id(self):
		return self.scpiget(":*idn?");


	## get/set current frequency
	#
	# @param freq - if this param is given, then the box is tuned to this freq. otherwise, the freq is queried
	# @return - the frequency of the box
	def freq(self, freq=None):
		if (freq == None):
			buf = self.scpiget("FREQ:CENTER?");
			freq = int(buf)
		else:
			self.scpiset(":FREQ:CENTER %d\n" % (freq))
			
		return freq


	## get/set frequency shift
	#
	# @param freq - if this param is given, then the frequency is shifted by this amount. otherwise, the freq shift is queried
	# @return - the amount of frequency shift
	def fshift(self, shift=None):
		if (shift == None):
			buf = self.scpiget("FREQ:SHIFT?");
			shift = float(buf)
		else:
			self.scpiset(":FREQ:SHIFT %d\n" % (shift))
			
		return shift


	## get/set decimation
	#
	# @param value - if this param is given, then the input signal is decimated by this amount. otherwise, the decimation is queried
	# @return - the amount of decimation
	def decimation(self, value=None):
		if (value == None):
			buf = self.scpiget("SENSE:DECIMATION?");
			value = int(buf)
		else:
			self.scpiset(":SENSE:DECIMATION %d\n" % (value))
			
		return value


	## get/set current gain
	#
	# @param gain - if this param is given, then the box is tuned to this freq. otherwise, the freq is queried
	# @return - the frequency of the box
	def gain(self, gain=None):
		if (gain == None):
			gain = self.scpiget("INPUT:GAIN:RF?");
		else:
			self.scpiset(":INPUT:GAIN:RF %s\n" % (gain))
			
		return gain


	## get/set current IF Gain
	#
	# @param gain - if this param is given, then the if of the box is set to this value. otherwise the gain is queried
	# @return - the ifgain in dB
	def ifgain(self, gain=None):
		if (gain == None):
			gain = self.scpiget(":INPUT:GAIN:IF?");
			gain = gain.partition(" ")
			gain = int(gain[0])
		else:
			self.scpiset(":INPUT:GAIN:IF %d\n" % (gain))
			
		return gain


	## flush any captures from the capture memory
	#
	def flush(self):
		self.scpiset(":sweep:flush\n")


	## get/set trigger settings
	#
	# @param gain - if this param is given, then the trigger settings are set as given.. if not, they are read
	# @return - the trigger settings set as an object
	def trigger(self, settings=None):
		if (settings == None):
			# find out what kind of trigger is set
			trigstr = self.scpiget(":TRIGGER:MODE?")
			if trigstr == "NONE":
				# build our return object
				settings = namedtuple("type")
				settings.type = "NONE"
				
			elif trigstr == "LEVEL":
				# build our return object
				settings = namedtuple("type", "fstart", "fstop", "amplitude")
				settings.type = "LEVEL"

				# read the settings from the box
				trigstr = self.scpiget(":TRIGGER:LEVEL?")
				(settings.fstart, settings.fstop, settings.amplitude) = trigstr.split(",")

			else:
				print "error: unsupported trigger type set: %s" % trigstr
				return None
			
		else:
			if settings.type == "NONE":
				self.scpiset(":TRIGGER:MODE NONE")

			elif settings.type == "LEVEL":
				self.scpiset(":TRIGGER:LEVEL %d, %d, %d" % (settings.fstart, settings.fstop, settings.amplitude))
				self.scpiset(":TRIGGER:MODE LEVEL")
			
		return settings


	## test for no more data
	## do a manual capture
	#
	# @param spp - the number of samples in a packet
	# @param ppb - the number of packets in a capture
	def capture(self, spp, ppb):
		self.scpiset(":TRACE:SPP %s\n" % (spp))
		self.scpiset(":TRACE:BLOCK:PACKETS %s\n" % (ppb))
		self.scpiset(":TRACE:BLOCK:DATA?\n")


	## aquire a read permission for reading data
	#
	# @return - 1 if allowed to read, 0 if not
	def request_read_perm(self):
		lockstr = self.scpiget(":SYSTEM:LOCK:REQUEST? ACQ\n")
		if lockstr == "1":
			return 1
		else:
			return 0


	## query to see if you have read permissions
	#
	# @return - 1 if allowed to read, 0 if not
	def have_read_perm(self):
		lockstr = self.scpiget(":SYSTEM:LOCK:HAVE? ACQ\n")
		if lockstr == "1":
			return 1
		else:
			return 0

	

	## test for no more data
	#
	# @return - 1 if no more data, 0 if more data
	def eof(self):
		return self.vrt.eof


	## has data
	#
	# @return - 1 if there is a packet to read.. 0 if not
	def has_data(self):
		return self.vrt.has_data()


	## read data
	#
	# @return - a packet object
	def read(self):
		return self.vrt.read_packet()


	## sweep add
	#
	# @param entry - the sweep entry to add
	def sweep_add(self, entry):
		self.scpiset(":sweep:entry:new")
		self.scpiset(":sweep:entry:freq:center %d, %d" % (entry.fstart, entry.fstop))
		self.scpiset(":sweep:entry:freq:step %d" % (entry.fstep))
		self.scpiset(":sweep:entry:freq:shift %d" % (entry.fshift))
		self.scpiset(":sweep:entry:decimation %d" % (entry.decimation))
		self.scpiset(":sweep:entry:antenna %d" % (entry.antenna))
		self.scpiset(":sweep:entry:gain:rf %s" % (entry.gain))
		self.scpiset(":sweep:entry:gain:if %d" % (entry.ifgain))
		self.scpiset(":sweep:entry:spp %d" % (entry.spp))
		self.scpiset(":sweep:entry:ppb %d" % (entry.ppb))
		self.scpiset(":sweep:entry:trigger:type %s" % (entry.trigtype))
		self.scpiset(":sweep:entry:trigger:level %d, %d, %d" % (entry.level_fstart, entry.level_fstop, entry.level_amplitude))
		self.scpiset(":sweep:entry:save")


	## sweep read
	#
	# @param index - the index of the entry to read
	# @return entry
	def sweep_read(self, index):
		ent = WSA4000SweepEntry.WSA4000SweepEntry()

		entrystr = self.scpiget(":sweep:entry:read? %d" % index)

		(value, sep, entrystr) = entrystr.partition(',')
		ent.fstart = int(value)
		(value, sep, entrystr) = entrystr.partition(',')
		ent.fstop = int(value)
		(value, sep, entrystr) = entrystr.partition(',')
		ent.fstep = int(value)
		(value, sep, entrystr) = entrystr.partition(',')
		ent.fshift = int(value)
		(value, sep, entrystr) = entrystr.partition(',')
		ent.decimation = int(value)
		(value, sep, entrystr) = entrystr.partition(',')
		ent.antenna = int(value)
		(ent.gain, sep, entrystr) = entrystr.partition(',')
		(value, sep, entrystr) = entrystr.partition(',')
		ent.ifgain = int(value)
		(value, sep, entrystr) = entrystr.partition(',')
		ent.spp = int(value)
		(value, sep, entrystr) = entrystr.partition(',')
		ent.ppb = int(value)
		(value, sep, entrystr) = entrystr.partition(',')
		ent.dwell_s = int(value)
		(value, sep, trigstr) = entrystr.partition(',')
		ent.dwell_us = int(value)
		
		if trigstr == "NONE":
			ent.trigtype = "NONE"
		else:
			(ent.trigtype, trigstr) = trigstr.split(',')
			if ent.trigtype == "LEVEL":
				(value, sep, trigstr) = trigstr.partition(',')
				ent.level_fstart = int(value)
				(value, sep, trigstr) = trigstr.partition(',')
				ent.level_fstop = int(value)
				(value, sep, trigstr) = trigstr.partition(',')
				ent.level_amplitude = int(value)

		return ent


	## flush the sweep list
	#
	def sweep_clear(self):
		self.scpiset(":sweep:entry:del all");


	## start the sweep engine
	#
	def sweep_start(self):
		self.scpiset(":sweep:list:start");


	## stop the sweep engine
	#
	def sweep_stop(self):
		self.scpiset(":sweep:list:stop");


	## flush capture memory of captures
	#
	def flush_captures(self):
		self.scpiset(":sweep:flush");


