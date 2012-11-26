import socket
from thinkrf.vrt import Stream
from thinkrf.config import SweepEntry, TriggerSettings, TriggerSettingsError

class WSA4000(object):

    def __init__(self):
        pass


    def connect(self, host):
        """
        connects to a wsa

        :param host: the hostname or IP to connect to
        """
        self._sock_scpi = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_scpi.connect((host, 37001))
        self._sock_scpi.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, True)
        self._sock_vrt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock_vrt.connect((host, 37000))
        self._vrt = Stream(self._sock_vrt)


    def disconnect(self):
        """
        close a connection to a wsa
        """
        self._sock_scpi.shutdown(socket.SHUT_RDWR)
        self._sock_scpi.close()
        self._sock_vrt.shutdown(socket.SHUT_RDWR)
        self._sock_vrt.close()


    def scpiset(self, cmd):
        """
        send a scpi command

        :param cmd: the command to send
        """
        self._sock_scpi.send("%s\n" % cmd)


    def scpiget(self, cmd):
        """
        get a scpi command

        :param cmd: the command to send
        :returns: the response back from the box if any
        """
        self._sock_scpi.send("%s\n" % cmd)
        buf = self._sock_scpi.recv(1024)
        return buf


    def id(self):
        """
        get the box identification string

        :returns: the id string
        """
        return self.scpiget(":*idn?")


    def freq(self, freq=None):
        """
        get/set current frequency

        :param freq: if this param is given, then the box is tuned to this freq. otherwise, the freq is queried
        :returns: the frequency of the box
        """
        if freq is None:
            buf = self.scpiget("FREQ:CENTER?")
            freq = int(buf)
        else:
            self.scpiset(":FREQ:CENTER %d\n" % freq)

        return freq


    def fshift(self, shift=None):
        """
        get/set frequency shift

        :param freq: if this param is given, then the frequency is shifted by this amount. otherwise, the freq shift is queried
        :returns: the amount of frequency shift
        """
        if shift is None:
            buf = self.scpiget("FREQ:SHIFT?")
            shift = float(buf)
        else:
            self.scpiset(":FREQ:SHIFT %d\n" % shift)

        return shift


    def decimation(self, value=None):
        """
        get/set decimation

        :param value: if this param is given, then the input signal is decimated by this amount. otherwise, the decimation is queried
        :returns: the amount of decimation
        """
        if value is None:
            buf = self.scpiget("SENSE:DECIMATION?")
            value = int(buf)
        else:
            self.scpiset(":SENSE:DECIMATION %d\n" % value)

        return value


    def gain(self, gain=None):
        """
        get/set current gain

        :param gain: if this param is given, then the box is tuned to this freq. otherwise, the freq is queried
        :returns: the frequency of the box
        """
        if gain is None:
            gain = self.scpiget("INPUT:GAIN:RF?")
        else:
            self.scpiset(":INPUT:GAIN:RF %s\n" % gain)

        return gain


    def ifgain(self, gain=None):
        """
        get/set current IF Gain

        :param gain: if this param is given, then the if of the box is set to this value. otherwise the gain is queried
        :returns: the ifgain in dB
        """
        if gain is None:
            gain = self.scpiget(":INPUT:GAIN:IF?")
            gain = gain.partition(" ")
            gain = int(gain[0])
        else:
            self.scpiset(":INPUT:GAIN:IF %d\n" % gain)

        return gain


    def flush(self):
        """
        flush any captures from the capture memory

        """
        self.scpiset(":sweep:flush\n")


    def trigger(self, settings=None):
        """
        This command sets or queries the type of trigger event.
        Setting the trigger type to "NONE" is equivalent to disabling
        the trigger execution; setting to any other type will
        enable the trigger engine.

        :param settings: if this param is given, then the trigger settings are set as given.. if not, they are read
        :type settings: thinkrf.config.TriggerSettings
        :returns: the trigger settings set as an object
        """
        if settings is None:
            # find out what kind of trigger is set
            trigstr = self.scpiget(":TRIGGER:MODE?")
            if trigstr == "NONE":
                settings = TriggerSettings("NONE")

            elif trigstr == "LEVEL":
                # build our return object
                settings = TriggerSettings("LEVEL")

                # read the settings from the box
                trigstr = self.scpiget(":TRIGGER:LEVEL?")
                settings.fstart, settings.fstop, settings.amplitude = trigstr.split(",")

            else:
                raise TriggerSettingsError("unsupported trigger type set: %s" % trigstr)

        else:
            if settings.trigtype == "NONE":
                self.scpiset(":TRIGGER:MODE NONE")

            elif settings.trigtype == "LEVEL":
                self.scpiset(":TRIGGER:LEVEL %d, %d, %d" % (settings.fstart, settings.fstop, settings.amplitude))
                self.scpiset(":TRIGGER:MODE LEVEL")

        return settings


    def capture(self, spp, ppb):
        """
        test for no more data
        do a manual capture

        :param spp: the number of samples in a packet
        :param ppb: the number of packets in a capture
        """
        self.scpiset(":TRACE:SPP %s\n" % (spp))
        self.scpiset(":TRACE:BLOCK:PACKETS %s\n" % (ppb))
        self.scpiset(":TRACE:BLOCK:DATA?\n")


    def request_read_perm(self):
        """
        aquire a read permission for reading data

        :returns: True if allowed to read, False if not
        """
        lockstr = self.scpiget(":SYSTEM:LOCK:REQUEST? ACQ\n")
        return lockstr == "1"


    def have_read_perm(self):
        """
        query to see if you have read permissions

        :returns: True if allowed to read, False if not
        """
        lockstr = self.scpiget(":SYSTEM:LOCK:HAVE? ACQ\n")
        return lockstr == "1"



    def eof(self):
        """
        test for no more data

        :returns: True if no more data, False if more data
        """
        return self._vrt.eof


    def has_data(self):
        """
        has data

        :returns: True if there is a packet to read, False if not
        """
        return self._vrt.has_data()


    def locked(self, modulestr):
        """
        get lock status

        :param modulestr: 'vco' for rf lock status.. clkref for mobo lock status
        :returns: 1 if locked.. 0 if not locked, -1 on error
        """
        if modulestr.upper() == 'VCO':
            buf = self.scpiget("SENSE:LOCK:RF?")
            return int(buf)
        elif modulestr.upper() == 'CLKREF':
            buf = self.scpiget("SENSE:LOCK:REFERENCE?")
            return int(buf)
        else:
            return -1


    def read(self):
        """
        read data

        :returns: a packet object
        """
        return self._vrt.read_packet()


    def raw_read(self, num):
        """
        raw read of socket data

        :param num: the number of bytes to read
        :returns: an array of bytes
        """
        return self._sock_vrt.recv(num)


    def sweep_add(self, entry):
        """
        sweep add

        :param entry: the sweep entry to add
        """
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


    def sweep_read(self, index):
        """
        sweep read

        :param index: the index of the entry to read
        :returns: entry
        """
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


    def sweep_clear(self):
        """
        flush the sweep list
        """
        self.scpiset(":sweep:entry:del all")


    def sweep_start(self, start_id = None):
        """
        start the sweep engine
        """
        if start_id:
            self.scpiset(":sweep:list:start %d" % start_id);
        else:
            self.scpiset(":sweep:list:start");


    def sweep_stop(self):
        """
        stop the sweep engine
        """
        self.scpiset(":sweep:list:stop")


    def flush_captures(self):
        """
        flush capture memory of captures
        """
        self.scpiset(":sweep:flush")


