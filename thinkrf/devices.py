import socket
from thinkrf.vrt import Stream
from thinkrf.config import SweepEntry, TriggerSettings, TriggerSettingsError

class WSA4000(object):
    """
    Interface for WSA4000

    :meth:`.connect` must be called before other methods are used.
    """

    ADC_DYNAMIC_RANGE = 72.5

    def __init__(self):
        pass


    def connect(self, host):
        """
        connect to a wsa

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
        Send a SCPI command.

        This is the lowest-level interface provided.
        Please see the Programmer's Guide for information about
        the commands available.

        :param cmd: the command to send
        :type cmd: str
        """
        self._sock_scpi.send("%s\n" % cmd)


    def scpiget(self, cmd):
        """
        Send a SCPI command and wait for the response.

        This is the lowest-level interface provided.
        Please see the Programmer's Guide for information about
        the commands available.

        :param cmd: the command to send
        :type cmd: str
        :returns: the response back from the box if any
        """
        self._sock_scpi.send("%s\n" % cmd)
        buf = self._sock_scpi.recv(1024)
        return buf


    def id(self):
        """
        Returns the WSA4000's identification information string.

        :returns: "<Manufacturer>,<Model>,<Serial number>,<Firmware version>"
        """
        return self.scpiget(":*idn?")


    def freq(self, freq=None):
        """
        This command sets or queries the tuned center frequency of the WSA.

        :param freq: the new center frequency in Hz (0 - 10 GHz); None to query

        :type freq: int
        :returns: the frequency in Hz
        """
        if freq is None:
            buf = self.scpiget("FREQ:CENTER?")
            freq = int(buf)
        else:
            self.scpiset(":FREQ:CENTER %d\n" % freq)

        return freq


    def fshift(self, shift=None):
        """
        This command sets or queries the frequency shift value.

        :param freq: the new frequency shift in Hz (0 - 125 MHz); None to query
        :type freq: int
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
        This command sets or queries the rate of decimation of samples in
        a trace capture. This decimation method consists of cascaded
        integrator-comb (CIC) filters and at every
        *value* number of samples, one sample is captured. The supported
        rate is 4 - 1023.  When the rate is set to 1, no decimation is
        performed on the trace capture.

        :param value: new decimation value (1 or 4 - 1023); None to query
        :type value: int
        :returns: the decimation value
        """
        if value is None:
            buf = self.scpiget("SENSE:DECIMATION?")
            value = int(buf)
        else:
            self.scpiset(":SENSE:DECIMATION %d\n" % value)
            if value == 1:
                # verify decimation was disabled correctly
                if int(self.scpiget("SENSE:DECIMATION?")) != 1:
                    # firmware < 2.5.3
                    self.scpiset(":SENSE:DECIMATION %d\n" % 0)

        # firmware < 2.5.3 returned 0 instead of 1
        if value == 0:
            value = 1

        return value


    def gain(self, gain=None):
        """
        This command sets or queries RFE quantized gain configuration.
        The RF front end (RFE) of the WSA4000 consists of multiple quantized
        gain stages. The gain corresponding to each user-selectable setting
        has been pre-calculated for either optimal sensitivity or linearity.
        The parameter defines the total quantized gain of the RFE.

        :param gain: 'high', 'medium', 'low' or 'vlow' to set; None to query
        :returns: the RF gain value
        """
        if gain is None:
            gain = self.scpiget("INPUT:GAIN:RF?")
        else:
            self.scpiset(":INPUT:GAIN:RF %s\n" % gain)

        return gain.lower()


    def ifgain(self, gain=None):
        """
        This command sets or queries variable IF gain stages of the RFE.
        The gain has a range of -10 to 34 dB. This stage of the gain is
        additive with the primary gain stages of the LNA
        that are described in :meth:`gain`.

        :param gain: float between -10 and 34 to set; None to query
        :returns: the ifgain in dB
        """
        if gain is None:
            gain = self.scpiget(":INPUT:GAIN:IF?")
            gain = gain.partition(" ")
            gain = int(gain[0])
        else:
            self.scpiset(":INPUT:GAIN:IF %d\n" % gain)

        return gain


    def preselect_filter(self, enable=None):
        """
        This command sets or queries the RFE preselect filter selection.

        :param enable: True or False to set; None to query
        :returns: the RFE preselect filter selection state
        """
        if enable is None:
            enable = self.scpiget(":INPUT:FILTER:PRESELECT?")
            enable = bool(int(enable))
        else:
            self.scpiset(":INPUT:FILTER:PRESELECT %d" % int(enable))
        return enable


    def antenna(self, number=None):
        """
        This command selects and queries the active antenna port.

        :param number: 1 or 2 to set; None to query
        :returns: active antenna port
        """
        if number is None:
            number = self.scpiget(":INPUT:ANTENNA?")
            number = int(number)
        else:
            self.scpiset(":INPUT:ANTENNA %d" % number)
        return number


    def reset(self):
        """
        Resets the WSA4000 to its default settings. It does not affect
        the registers or queues associated with the IEEE mandated commands.
        """
        self.scpiset(":*rst")


    def flush(self):
        """
        Flush capture memory of sweep captures.
        """
        self.scpiset(":sweep:flush\n")


    def trigger(self, settings=None):
        """
        This command sets or queries the type of trigger event.
        Setting the trigger type to "NONE" is equivalent to disabling
        the trigger execution; setting to any other type will
        enable the trigger engine.

        :param settings: the new trigger settings; None to query
        :type settings: thinkrf.config.TriggerSettings
        :returns: the trigger settings
        """
        if settings is None:
            # find out what kind of trigger is set
            trigstr = self.scpiget(":TRIGGER:TYPE?")
            if trigstr == "NONE":
                settings = TriggerSettings("NONE")

            elif trigstr == "LEVEL":
                # build our return object
                settings = TriggerSettings("LEVEL")

                # read the settings from the box
                trigstr = self.scpiget(":TRIGGER:LEVEL?")
                settings.fstart, settings.fstop, settings.amplitude = trigstr.split(",")

                # convert to integers
                settings.fstart = int(settings.fstart)
                settings.fstop = int(settings.fstop)
                settings.amplitude = float(settings.amplitude)

            else:
                raise TriggerSettingsError("unsupported trigger type set: %s" % trigstr)

        else:
            if settings.trigtype == "NONE":
                self.scpiset(":TRIGGER:TYPE NONE")

            elif settings.trigtype == "LEVEL":
                self.scpiset(":TRIGGER:LEVEL %d, %d, %d" % (settings.fstart, settings.fstop, settings.amplitude))
                self.scpiset(":TRIGGER:TYPE LEVEL")

        return settings



    def capture(self, spp, ppb):
        """
        This command will start the single block capture and the return of
        *ppb* packets of *spp* samples each. The data
        within a single block capture trace is continuous from one packet
        to the other, but not necessary between successive block capture
        commands issued.

        :param spp: the number of samples in a packet
        :param ppb: the number of packets in a capture
        """
        self.scpiset(":TRACE:SPP %s\n" % (spp))
        self.scpiset(":TRACE:BLOCK:PACKETS %s\n" % (ppb))
        self.scpiset(":TRACE:BLOCK:DATA?\n")


    def request_read_perm(self):
        """
        Aquire exclusive permission to read data from the WSA.

        :returns: True if allowed to read, False if not
        """
        lockstr = self.scpiget(":SYSTEM:LOCK:REQUEST? ACQ\n")
        return lockstr == "1"


    def have_read_perm(self):
        """
        Check if we have permission to read data.

        :returns: True if allowed to read, False if not
        """
        lockstr = self.scpiget(":SYSTEM:LOCK:HAVE? ACQ\n")
        return lockstr == "1"



    def eof(self):
        """
        Check if the VRT stream has closed.

        :returns: True if no more data, False if more data
        """
        return self._vrt.eof


    def has_data(self):
        """
        Check if there is VRT data to read.

        :returns: True if there is a packet to read, False if not
        """
        return self._vrt.has_data()


    def locked(self, modulestr):
        """
        This command queries the lock status of the RF VCO (Voltage Control
        Oscillator) in the Radio Front End (RFE) or the lock status of the
        PLL reference clock in the digital card.

        :param modulestr: 'vco' for rf lock status, 'clkref' for mobo lock status
        :returns: True if locked
        """
        if modulestr.upper() == 'VCO':
            buf = self.scpiget("SENSE:LOCK:RF?")
            return bool(int(buf))
        elif modulestr.upper() == 'CLKREF':
            buf = self.scpiget("SENSE:LOCK:REFERENCE?")
            return bool(int(buf))
        else:
            return -1


    def read(self):
        """
        Read a single VRT packet from the WSA.

        See :meth:`thinkrf.vrt.Stream.read_packet`.
        """
        return self._vrt.read_packet()


    def raw_read(self, num):
        """
        Raw read of VRT socket data from the WSA.

        :param num: the number of bytes to read
        :returns: bytes
        """
        return self._sock_vrt.recv(num)


    def sweep_add(self, entry):
        """
        Add an entry to the sweep list

        :param entry: the sweep entry to add
        :type entry: thinkrf.config.SweepEntry
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
        Read an entry from the sweep list.

        :param index: the index of the entry to read
        :returns: sweep entry
        :rtype: thinkrf.config.SweepEntry
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
        Remove all entries from the sweep list.
        """
        self.scpiset(":sweep:entry:del all")


    def sweep_start(self, start_id = None):
        """
        Start the sweep engine.
        """
        if start_id:
            self.scpiset(":sweep:list:start %d" % start_id);
        else:
            self.scpiset(":sweep:list:start");


    def sweep_stop(self):
        """
        Stop the sweep engine.
        """
        self.scpiset(":sweep:list:stop")


    def flush_captures(self):
        """
        Flush capture memory of sweep captures.
        """
        self.scpiset(":sweep:flush")


