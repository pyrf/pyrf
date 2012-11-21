import socket
from thinkrf.vrt import Stream
from thinkrf.config import SweepEntry, Settings

class WSA4000(object):

    def __init__(self):
        pass


    ## connects to a wsa
    #
    # @param host - the hostname or IP to connect to
    def connect(self, host):
        self._sock_scpi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_scpi.connect((host, 37001))
        self._sock_scpi.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self._sock_vrt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_vrt.connect((host, 37000))
        self._vrt = Stream(self._sock_vrt)


    ## close a connection to a wsa
    #
    def disconnect(self):
        self._sock_scpi.shutdown(socket.SHUT_RDWR)
        self._sock_scpi.close()
        self._sock_vrt.shutdown(socket.SHUT_RDWR)
        self._sock_vrt.close()


    ## send a scpi command
    #
    # @param cmd - the command to send
    def scpiset(self, cmd):
        self._sock_scpi.send("%s\n" % cmd)


    ## get a scpi command
    #
    # @param cmd - the command to send
    # @return - the response back from the box if any
    def scpiget(self, cmd):
        self._sock_scpi.send("%s\n" % cmd)
        buf = self._sock_scpi.recv(1024)
        return buf


    ## get the box identification string
    #
    # @return - the id string
    def id(self):
        return self.scpiget(":*idn?")


    ## get/set current frequency
    #
    # @param freq - if this param is given, then the box is tuned to this freq. otherwise, the freq is queried
    # @return - the frequency of the box
    def freq(self, freq=None):
        if freq is None:
            buf = self.scpiget("FREQ:CENTER?")
            freq = int(buf)
        else:
            self.scpiset(":FREQ:CENTER %d\n" % freq)

        return freq


    ## get/set frequency shift
    #
    # @param freq - if this param is given, then the frequency is shifted by this amount. otherwise, the freq shift is queried
    # @return - the amount of frequency shift
    def fshift(self, shift=None):
        if shift is None:
            buf = self.scpiget("FREQ:SHIFT?")
            shift = float(buf)
        else:
            self.scpiset(":FREQ:SHIFT %d\n" % shift)

        return shift


    ## get/set decimation
    #
    # @param value - if this param is given, then the input signal is decimated by this amount. otherwise, the decimation is queried
    # @return - the amount of decimation
    def decimation(self, value=None):
        if value is None:
            buf = self.scpiget("SENSE:DECIMATION?")
            value = int(buf)
        else:
            self.scpiset(":SENSE:DECIMATION %d\n" % value)

        return value


    ## get/set current gain
    #
    # @param gain - if this param is given, then the box is tuned to this freq. otherwise, the freq is queried
    # @return - the frequency of the box
    def gain(self, gain=None):
        if gain is None:
            gain = self.scpiget("INPUT:GAIN:RF?")
        else:
            self.scpiset(":INPUT:GAIN:RF %s\n" % gain)

        return gain


    ## get/set current IF Gain
    #
    # @param gain - if this param is given, then the if of the box is set to this value. otherwise the gain is queried
    # @return - the ifgain in dB
    def ifgain(self, gain=None):
        if gain is None:
            gain = self.scpiget(":INPUT:GAIN:IF?")
            gain = gain.partition(" ")
            gain = int(gain[0])
        else:
            self.scpiset(":INPUT:GAIN:IF %d\n" % gain)

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
        if settings is None:
            # find out what kind of trigger is set
            trigstr = self.scpiget(":TRIGGER:MODE?")
            if trigstr == "NONE":
                # build our return object
                settings = Settings()
                settings.type = "NONE"

            elif trigstr == "LEVEL":
                # build our return object
                settings = Settings()
                settings.type = "LEVEL"

                # read the settings from the box
                trigstr = self.scpiget(":TRIGGER:LEVEL?")
                settings.fstart, settings.fstop, settings.amplitude = trigstr.split(",")

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
    # @return - True if allowed to read, False if not
    def request_read_perm(self):
        lockstr = self.scpiget(":SYSTEM:LOCK:REQUEST? ACQ\n")
        return lockstr == "1"


    ## query to see if you have read permissions
    #
    # @return - True if allowed to read, False if not
    def have_read_perm(self):
        lockstr = self.scpiget(":SYSTEM:LOCK:HAVE? ACQ\n")
        return lockstr == "1"



    ## test for no more data
    #
    # @return - True if no more data, False if more data
    def eof(self):
        return self._vrt.eof


    ## has data
    #
    # @return - True if there is a packet to read, False if not
    def has_data(self):
        return self._vrt.has_data()


    ## get lock status
    #
    # @param modulestr - 'vco' for rf lock status.. clkref for mobo lock status
    # @return - 1 if locked.. 0 if not locked, -1 on error
    def locked(self, modulestr):
        if modulestr.upper() == 'VCO':
            buf = self.scpiget("SENSE:LOCK:RF?")
            return int(buf)
        elif modulestr.upper() == 'CLKREF':
            buf = self.scpiget("SENSE:LOCK:REFERENCE?")
            return int(buf)
        else:
            return -1


    ## read data
    #
    # @return - a packet object
    def read(self):
        return self._vrt.read_packet()


    ## raw read of socket data
    #
    # @param num - the number of bytes to read
    # @return - an array of bytes
    def raw_read(self, num):
        return self._sock_vrt.recv(num)


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
        ent = SweepEntry()

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
        self.scpiset(":sweep:entry:del all")


    ## start the sweep engine
    #
    def sweep_start(self, start_id = None):
        if start_id:
            self.scpiset(":sweep:list:start %d" % start_id);
        else:
            self.scpiset(":sweep:list:start");


    ## stop the sweep engine
    #
    def sweep_stop(self):
        self.scpiset(":sweep:list:stop")


    ## flush capture memory of captures
    #
    def flush_captures(self):
        self.scpiset(":sweep:flush")


