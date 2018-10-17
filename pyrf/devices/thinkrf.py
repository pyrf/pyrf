from pyrf.config import SweepEntry, TriggerSettings, TRIGGER_TYPE_LEVEL, TRIGGER_TYPE_NONE, TriggerSettingsError
from pyrf.connectors.blocking import PlainSocketConnector
from pyrf.connectors.base import sync_async
from pyrf.vrt import vrt_packet_reader
from pyrf.devices.thinkrf_properties import wsa_properties
from pyrf.util import capture_spectrum, read_data_and_context
from pyrf.numpy_util import compute_fft
import struct
import socket
import select
import platform
import numpy as np

DISCOVERY_UDP_PORT = 18331
_DISCOVERY_QUERY_CODE = 0x93315555
_DISCOVERY_QUERY_VERSION = 2
_DISCOVERY_QUERY_FORMAT = '>LL'
DISCOVERY_QUERY = struct.pack(_DISCOVERY_QUERY_FORMAT,
    _DISCOVERY_QUERY_CODE, _DISCOVERY_QUERY_VERSION)

class WSA(object):
    """
    Interface for ThinkRF's R5500, R5700, and WSA5000 (EOL).

    :param connector: Connector object to use for SCPI/VRT connections,
        defaults to a new
        :class:`PlainSocketConnector <pyrf.connectors.blocking.PlainSocketConnector>`
        instance

    :meth:`connect()` must be called before other methods are used.

    .. note::

       The following methods will either block then return a result
       or if you passed a
       :class:`TwistedConnector <pyrf.connectors.twisted_async.TwistedConnector>`
       instance to the constructor, they will immediately return a
       Twisted Deferred object.

    """

    properties = None

    def __init__(self, connector=None):
        if not connector:
            connector = PlainSocketConnector()
        self.connector = connector
        self._output_file = None

    def async_connector(self):
        """
        Return True if the connector being used is asynchronous
        """
        return hasattr(self.connector, 'vrt_callback')

    def set_async_callback(self, callback):
        self.connector.vrt_callback = callback

    def set_recording_output(self, output_file=None):
        """
        Dump a recording of all the received packets to output_file
        """
        self.connector.set_recording_output(output_file)
        self._output_file = output_file

    def inject_recording_state(self, state):
        """
        Inject the current RTSA state into the recording stream when
        the next capture is received.  Replaces previous data if not
        yet sent.
        """
        self.connector.inject_recording_state(state)

    @sync_async
    def connect(self, host):
        """
        Connect to an RTSA (aka WSA).
        :param host: the hostname or IP to connect to
        """
        yield self.connector.connect(host)
        self.device_id = (yield self.scpiget(":*idn?"))
        self.properties = wsa_properties(self.device_id)

        self.fw_version = self.device_id.split(',')[-1]
        self.device_state = {}

    def disconnect(self):
        """
        Close a connection to an RTSA (aka WSA).
        """
        self.connector.disconnect()
        if self.properties:
            del self.properties

    def scpiset(self, cmd):
        """
        Send a SCPI command of set type (i.e. not query command).

        This is the lowest-level interface provided.  See the product's
        Programmer's Guide for the SCPI commands available.

        :param cmd: the command to send
        :type cmd: str
        """
        self.connector.scpiset(cmd)

    def scpiget(self, cmd):
        """
        Send a SCPI *query* command and wait for the response.

        This is the lowest-level interface provided.  See the product's
        Programmer's Guide for the SCPI commands available.

        :param cmd: the command to send
        :type cmd: str
        :returns: the response back from the box if any
        """
        return self.connector.scpiget(cmd)

    @sync_async
    def id(self):
        """
        Returns the RTSA's identification information string.

        :returns: "<Manufacturer>,<Model>,<Serial number>,<Firmware version>"
        """
        yield self.scpiget(":*idn?")

    def peakfind(self, n=1, rbw=None, average=1):
        """
        Returns frequency and the power level of the maximum spectral point
        computed using the current settings, Note this function disables

        :param n: determine the number of peaks to return
        :param rbw: rbw of spectral capture (Hz) (will round to nearest native RBW)
        :param average: number of capture iterations
        :returns: [(peak_freq1, peak_power1),
                   (peak_freq2, peak_power2)
                   , ...,
                   (peak_freqn, peak_powern)]
        """
        iq_path = self.iq_output_path()
        capture_mode = self.capture_mode()

        if not iq_path == 'DIGITIZER' or not capture_mode == 'BLOCK':
            raise StandardError("Can't perform peak find while RTSA is sweeping or IQ path is not on the DIGITIZER path")
        # get read access
        self.request_read_perm()

        fstart, fstop, pow_data = capture_spectrum(self, rbw, average)
        frequencies = np.linspace(fstart, fstop, len(pow_data))
        peak_points = []
        for p in sorted(pow_data, reverse=True)[0:n]:
            peak_points.append((frequencies[np.where(pow_data == p)][0], p))
        return peak_points

    def measure_noisefloor(self, rbw=None, average=1):
        """
        Returns a power level that represents the top edge of the noisefloor

        :param rbw: rbw of spectral capture (Hz) (will round to nearest native RBW)
        :param average: number of capture iterations
        :returns: noise_power
        """
        iq_path = self.iq_output_path()
        capture_mode = self.capture_mode()

        if not iq_path == 'DIGITIZER' or not capture_mode == 'BLOCK':
            raise StandardError("Can't measure noisefloor while RTSA is sweeping or IQ path is not on the DIGITIZER path")
        # get read access
        self.request_read_perm()
        fstart, fstop, pow_data = capture_spectrum(self, rbw, average)
        noisefloor = np.mean(sorted(pow_data)[int(len(pow_data) * 0.2):])
        return noisefloor

    @sync_async
    def rfe_mode(self, mode=None):
        """
        This command sets or queries the RTSA's Receiver Front End (RFE) mode of
        operation.

        :param mode: 'ZIF', 'DD', 'HDR', 'IQIN', 'SH' or None to query
        :returns: the current RFE mode
        """
        if mode is None:
            buf = yield self.scpiget(":INPUT:MODE?")
            mode = buf.strip()
        else:
            self.scpiset(":INPUT:MODE %s" % str(mode))
        yield mode

    @sync_async
    def iq_output_path(self, path=None):
        """
        This command sets or queries the RTSA's current IQ path.  It is not applicable to R5700.

        :param path: 'DIGITIZER', 'CONNECTOR', 'HIF', or None to query
        :returns: the current IQ path
        """
        if 'R5500' in self.properties.model:
            cmd = "OUTPUT:MODE"
        else:
            cmd = "OUTPUT:IQ:MODE"
        if path is None:
            buf = yield self.scpiget("%s?" % cmd)
            path = buf.strip()
        else:
            self.scpiset("%s %s" % (cmd, path))
        yield path

    @sync_async
    def capture_mode(self):
        """
        This command queries the current capture mode

        :returns: the current capture mode
        """

        buf = yield self.scpiget(":SYST:CAPTURE:MODE?")
        path = buf.strip()
        yield path

    @sync_async
    def pll_reference(self, src=None):
        """
        This command sets or queries the RTSA's PLL reference source

        :param src: 'INT', 'EXT', 'GPS' (when available with the model) or None to query
        :returns: the current PLL reference source
        """

        if src is None:
            buf = yield self.scpiget(":SOURCE:REFERENCE:PLL?")
            src = buf.strip()
        else:
            assert src in ('INT', 'EXT')
            self.scpiset(":SOURCE:REFERENCE:PLL %s" % src)
        yield src

    @sync_async
    def freq(self, freq=None):
        """
        This command sets or queries the tuned center frequency of the RTSA.

        :param freq: the center frequency in Hz (range vary depnding on the product model); None to query

        :type freq: int
        :returns: the frequency in Hz
        """
        if freq is None:
            buf = yield self.scpiget(":FREQ:CENTER?")
            freq = int(buf)
        else:
            self.scpiset(":FREQ:CENTER %d\n" % freq)

        yield freq

    @sync_async
    def fshift(self, shift=None):
        """
        This command sets or queries the frequency shift value.

        :param freq: the frequency shift in Hz (0 - 125 MHz); None to query
        :type freq: int
        :returns: the amount of frequency shift
        """
        if shift is None:
            buf = yield self.scpiget("FREQ:SHIFT?")
            shift = float(buf)
        else:
            self.scpiset(":FREQ:SHIFT %d\n" % shift)

        yield shift

    @sync_async
    def decimation(self, value=None):
        """
        This command sets or queries the rate of decimation of samples in
        a trace capture. The supported rate is 4 - 1024.  When the rate is
        set to 1, no decimation is performed on the trace capture.

        :param value: new decimation value (1 or 4 - 1024); None to query
        :type value: int
        :returns: the decimation value
        """
        if value is None:
            buf = yield self.scpiget("SENSE:DECIMATION?")
            value = int(buf)
        else:
            self.scpiset(":SENSE:DECIMATION %d\n" % value)
            if value == 1:
                # verify decimation was disabled correctly
                actual = yield self.scpiget("SENSE:DECIMATION?")
                if int(actual) != 1:
                    # firmware < 2.5.3
                    self.scpiset(":SENSE:DECIMATION %d\n" % 0)

        # firmware < 2.5.3 returned 0 instead of 1
        if value == 0:
            value = 1

        yield value

    @sync_async
    def psfm_gain(self, gain = None):
        GAIN_STATE = {('1', '1'): 'high',
                      ('1', '0'): 'medium',
                      ('0', '0'): 'low'}
        GAIN_SET = {v: k for k, v in GAIN_STATE.items()}
        """
        This command sets or queries one of the PSFM gain stages.

        :param gain: sets the gain value of the amplifiers, note the
        gain values have to be either 'high', 'medium', 'low'
        :returns: the RF gain value
        """

        if gain is None:
            gain1 = yield self.scpiget(":INP:GAIN? 1")
            gain2 = yield self.scpiget(":INP:GAIN? 2")
            gain = GAIN_STATE[(gain1[0], gain2[0])]
        else:
            state = GAIN_SET[gain.lower()]
            self.scpiset(":INPUT:GAIN 1 %s\n" % state[0])
            self.scpiset(":INPUT:GAIN 2 %s\n" % state[1])

        yield gain

    @sync_async
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
            gain = yield self.scpiget(":INPUT:GAIN:IF?")
            gain = gain.partition(" ")
            gain = int(gain[0])
        else:
            self.scpiset(":INPUT:GAIN:IF %d\n" % gain)

        yield gain

    @sync_async
    def hdr_gain(self, gain=None):
        """
        This command sets or queries the HDR gain of the receiver.
        The gain has a range of -10 to 30 dB.

        :param gain: float between -10 and 30 to set; None to query
        :returns: the hdr gain in dB
        """
        if gain is None:
            gain = yield self.scpiget(":INPut:GAIN:HDR?")
            gain = gain.partition(" ")
            gain = int(gain[0])
        else:
            self.scpiset(":INPut:GAIN:HDR %d\n" % gain)

        yield gain

    @sync_async
    def preselect_filter(self, enable=None):
        """
        This command sets or queries the RFE preselect filter selection
        when supported by the model.

        :param enable: True or False to set; None to query
        :returns: the RFE preselect filter selection state
        """
        if enable is None:
            enable = yield self.scpiget(":INPUT:FILTER:PRESELECT?")
            enable = bool(int(enable))
        else:
            self.scpiset(":INPUT:FILTER:PRESELECT %d" % int(enable))
        yield enable

    def reset(self):
        """
        Resets the RTSA to its default settings. It does not affect
        the registers or queues associated with the IEEE mandated commands.
        """
        self.scpiset(":*rst")

    def abort(self):
        """
        This command will cause the RTSA to stop the data capturing,
        whether in the manual trace block capture, triggering or sweeping
        mode.  The RTSA will be put into the manual mode; in other
        words, process such as streaming, trigger and sweep will be
        stopped.  The capturing process does not wait until the end of a
        packet to stop, it will stop immediately upon receiving the command.
        """
        self.scpiset(":SYSTEM:ABORT")


    def flush(self):
        """
        This command clears the RTSA's internal data storage buffer of
        any data that is waiting to be sent.  Thus, it is recommended that
        the flush command should be used when switching between different
        capture modes to clear up the remnants of captured packets.
        """
        self.scpiset(":SYSTEM:FLUSH")

    @sync_async
    def trigger(self, settings=None):
        """
        This command sets or queries the type of trigger event.
        Setting the trigger type to "NONE" is equivalent to disabling
        the trigger execution; setting to any other type will
        enable the trigger engine.

        :param settings: the new trigger settings; None to query
        :type settings: dictionary
        :returns: the trigger settings
        """
        if settings is None:
            # find out what kind of trigger is set
            trigstr = yield self.scpiget(":TRIGGER:TYPE?")
            if trigstr == "LEVEL":
                # read the settings from the box
                trigstr = yield self.scpiget(":TRIGGER:LEVEL?")
                settings = {"type": trigstr,
                            "fstart": int(trigstr.split(",")[0]),
                            "fstop": int(trigstr.split(",")[1]),
                            "amplitude": int(trigstr.split(",")[2])}
            else:
                settings = {"type": trigstr}
        else:
            self.scpiset(":TRIGGER:TYPE %s" % settings["type"])

            if settings["type"] == "LEVEL":
                self.scpiset(":TRIGGER:LEVEL %d, %d, %d" % (settings['fstart'],
                                                            settings['fstop'],
                                                            settings['amplitude']))
        yield settings

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


    @sync_async
    def spp(self, samples=None):
        """
        This command sets or queries the number of Samples Per Packet
        (SPPacket).

        The upper bound of the samples is limited by the VRT's 16-bit
        packet size field less the VRT header and any optional fields
        (i.e. Stream ID, Class ID, Timestamps, and trailer) of 32-bit
        wide words.  However since the SPP must be a multiple of 32,
        the maximum is thus limited by 2**16 - 32.

        :param samples: the number of samples in a packet or None
        :returns: the current spp value if the samples parameter is None
        """
        if samples is None:
            number = yield self.scpiget(":TRACE:SPP?")
            yield int(number)
        else:
            self.scpiset(":TRACE:SPP %s\n" % (samples,))

    @sync_async
    def ppb(self, packets=None):
        """
        This command sets the number of IQ packets in a capture
        block

        :param packets: the number of samples in a packet
        :returns: the current ppb value if the packets parameter is None
        """
        if packets is None:
            number = yield self.scpiget(":TRACE:BLOCK:PACKETS?")
            number = int(number)
            yield number
        else:
            self.scpiset(":TRACE:BLOCK:PACKETS %s\n" % (packets,))

    @sync_async
    def request_read_perm(self):
        """
        Acquire exclusive permission to read data from the RTSA.

        :returns: True if allowed to read, False if not
        """
        lockstr = yield self.scpiget(":SYSTEM:LOCK:REQUEST? ACQ\n")
        yield lockstr == "1"

    @sync_async
    def have_read_perm(self):
        """
        Check if we have permission to read data.

        :returns: True if allowed to read, False if not
        """
        lockstr = yield self.scpiget(":SYSTEM:LOCK:HAVE? ACQ\n")
        yield lockstr == "1"

    def read_data(self, spp):
        """
        Return data packet of *spp* (samples per packet) size, the associated context info and the computed power spetral data.

        :param spp: the number of samples in a packet
        :returns: data class, context dictionary, and power spectral data array
        """
        data, context = read_data_and_context(self, spp)
        pow_data = compute_fft(self, data, context)
        return data, context, pow_data

    def eof(self):
        """
        Check if the VRT stream has closed.

        :returns: True if no more data, False if more data
        """
        return self.connector.eof()


    def has_data(self):
        """
        Check if there is VRT data to read.

        :returns: True if there is a packet to read, False if not
        """
        return self.connector.has_data()

    @sync_async
    def locked(self, modulestr):
        """
        This command queries the lock status of the RF VCO (Voltage Control
        Oscillator) in the Radio Front End (RFE) or the lock status of the
        PLL reference clock in the digitizer card.

        :param modulestr: 'vco' for rf lock status, 'clkref' for mobo lock status
        :returns: True if locked
        """
        if modulestr.upper() == 'VCO':
            buf = yield self.scpiget("SENSE:LOCK:RF?")
            yield bool(int(buf))
        elif modulestr.upper() == 'CLKREF':
            buf = yield self.scpiget("SENSE:LOCK:REFERENCE?")
            yield bool(int(buf))
        else:
            yield -1

    @sync_async
    def read(self):
        """
        Read a single parsed VRT packet from the RTSA, either context or data.
        """
        return vrt_packet_reader(self.connector.raw_read)

    def raw_read(self, num):
        """
        Raw read of VRT socket data of *num* bytes from the RTSA.

        :param num: the number of bytes to read
        :returns: bytes
        """
        return self.connector.raw_read(num)

    def sweep_add(self, entry):
        """
        Add an entry to the sweep list

        :param entry: the sweep entry to add
        :type entry: pyrf.sweepDevice.sweepSettings
        """

        # create a new entry
        self.scpiset(":sweep:entry:new")

        # detect if variable attenuator needs to be set
        if self.properties.model in ['R5500-418', 'R5500-427']:
            self.scpiset("SWEEP:ENTRY:ATT:VAR %0.2f" % (entry.attenuation))

        else:
            self.scpiset(":sweep:entry:attenuator %0.2f" % (
                entry.attenuation))

        # set the samples per packet
        self.scpiset(":sweep:entry:spp %d" % (entry.spp))

        # create an entry for DD mode if required
        if entry.dd_mode:
            self.scpiset(":sweep:entry:mode DD")

            # if ZIF mode, double the sample size
            if entry.rfe_mode == 'ZIF':
                self.scpiset(":sweep:entry:spp %d" % (entry.spp * 2))
            self.scpiset(":sweep:entry:save")

        # if only a DD entry is required, don't make another entry
        if not entry.beyond_dd:
            return

        # set the SPP
        self.scpiset(":sweep:entry:spp %d" % (entry.spp))

        # set the RFE mode of the entry
        self.scpiset(":sweep:entry:mode %s" % (entry.rfe_mode))

        # set the center frequencies of fstart/fstop of the entry
        self.scpiset(":sweep:entry:freq:center %d, %d" % (entry.fstart, entry.fstop))

        # set the frequency step of the entry
        self.scpiset(":sweep:entry:freq:step %d" % (entry.fstep))

        # save the sweep entry
        self.scpiset(":sweep:entry:save")

        # determine if a stop frequency is required to capture last bit of spectrum
        if entry.make_end_entry:
            start_freq = entry.end_entry_freq
            stop_freq = entry.end_entry_freq + 100e3
            self.scpiset(":sweep:entry:freq:center %d, %d" % (start_freq, stop_freq))
            self.scpiset(":sweep:entry:save")

    @sync_async
    def sweep_read(self, index):
        """
        Read a sweep entry at the given sweep *index* from the sweep list.

        :param index: the index of the entry to read
        :returns: sweep entry
        :rtype: pyrf.config.SweepEntry
        """
        ent = SweepEntry()

        entrystr = yield self.scpiget(":sweep:entry:read? %d" % index)

        values = entrystr.split(',')
        for setting, value in zip(self.properties.SWEEP_SETTINGS, values):
            if setting not in ('gain', 'trigtype'):
                value = int(value)
            setattr(ent, setting, value)

        yield ent

    @sync_async
    def sweep_iterations(self, count=None):
        """
        Set or query the number of iterations to loop through a sweep list.

        :param count: the number of iterations, 0 for infinite
        :returns: the current number of iterations if count is None
        """
        if count is None:
            number = yield self.scpiget(":sweep:list:iterations?")
            yield int(number)
        else:
            self.scpiset(":sweep:list:iterations %d" % (count,))

    def sweep_clear(self):
        """
        Remove all entries from the sweep list.
        """
        self.scpiset(":sweep:entry:delete all")


    def sweep_start(self, start_id = None):
        """
        Start the sweep engine with an optional ID.

        :param start_id: An optional 32-bit ID to identify the sweep
        """
        if start_id:
            self.scpiset(":sweep:list:start %d" % start_id);
        else:
            self.scpiset(":sweep:list:start");


    def sweep_stop(self):
        """
        Stop the sweep engine. Recommend calling :meth:`flush()` after stopping.
        """
        self.scpiset(":sweep:list:stop")


    def flush_captures(self):
        """
        Flush capture memory of sweep captures.
        """
        self.scpiset(":SYSTEM:FLUSH")

    def stream_start(self, stream_id=None):
        """
        This command begins the execution of the stream capture.
        It will also initiate data capturing.  Data packets will
        be streamed (or pushed) from the RTSA whenever data
        is available.

        :param stream_id: optional unsigned 32-bit stream identifier
        """
        self.scpiset(':TRACE:STREAM:START' +
            (' %d' % stream_id if stream_id else ''))

    def stream_stop(self):
        """
        This command stops the stream capture.  After receiving
        the command, the RTSA system will stop when the current
        capturing VRT packet is completed. Recommend calling
        :meth:`flush()` after stopping.
        """
        self.scpiset(':TRACE:STREAM:STOP')

    @sync_async
    def stream_status(self):
        """
        This query returns the current running status of the
        stream capture mode.

        :returns: 'RUNNING' or 'STOPPED'
        """
        yield self.scpiget(":TRACE:STREAM:STATUS?")

    @sync_async
    def attenuator(self,  atten_val=None):
        """
        This command enables, disables or queries the RTSA's RFE attenuation.

        :param atten_val: see Programmer's Guide for the attenuation value to use for your product; None to query
        :returns: the current attenuation value
        """
        if 'R5500-418' in self.properties.model or 'R5500-427' in self.properties.model:
            cmd = 'INPUT:ATTENUATOR:VAR'
        else:
            cmd = 'INPUT:ATTENUATOR'

        if  atten_val is None:
            atten_val = yield self.scpiget("%s?" % cmd)
        else:
            if 'R5500' in self.properties.model:
                    atten_val = yield self.scpiset("%s %0.2f" % (cmd, atten_val))
            else:
                atten_val = bool(int( atten_val))
                self.scpiset(":INPUT:ATTENUATOR %s" % (1 if atten_val else 0))

        yield atten_val

    @sync_async
    def var_attenuator(self, atten_val=None):
        """
        This command sets the RTSA's variable attenuator (when applicable to the model)

        :param atten_val: attenuation value, vary depending on the product
        :returns: the current attenuation value
        """
        if atten_val is None:

                atten_val = yield self.scpiget("INP:ATT:VAR?")
        else:
                self.scpiset("INP:ATT:VAR %d" % atten_val)
        yield atten_val

    @sync_async
    def errors(self):
        """
        Flush and return the list of errors from past commands
        sent to the RTSA. An empty list is returned when no errors
        are present.
        """
        errors = []
        while True:
            error = yield self.scpiget(":SYSTEM:ERROR?")
            num, message = error.strip().split(',', 1)
            num = int(num)
            message = message.strip('"')
            if not num:
                break
            errors.append((num, message))
        yield errors

    def apply_device_settings(self, settings, force_change = False):
        """
        This command takes a dict of device settings, and applies them to the
        RTSA.
        Note: this method only applies a setting if it has been changed using this method
        :param settings: dict containing settings such as attenuation,decimation,etc
        :param force_change: to force the change update or not
        """
        device_setting = {
            'freq': self.freq,
            'psfm_gain': self.psfm_gain,
            'hdr_gain': self.hdr_gain,
            'ifgain': self.ifgain,
            'fshift': self.fshift,
            'decimation': self.decimation,
            'spp': self.spp,
            'ppb': self.ppb,
            'trigger': self.trigger,
            'attenuator': self.attenuator,
            'var_attenuator': self.var_attenuator,
            'rfe_mode': self.rfe_mode,
            'iq_output_path': self.iq_output_path,
            'pll_reference': self.pll_reference,
            'trigger': self.trigger,
            }

        for k, v in settings.iteritems():
            if force_change:
                self.device_state[k] = v
                device_setting[k](v)
            #FIXME: Find more elegant way to do this
            if not k in self.device_state:
                self.device_state[k] = v
                device_setting[k](v)
            if not self.device_state[k] == v:
                self.device_state[k] = v
                device_setting[k](v)

def parse_discovery_response(response):
    """
    This function parses the RTSA's raw discovery response

    :param response: The RTSA's raw response to a discovery query
    :returns: Return (model, serial, firmware version) based on a discovery
    response message
    """
    RESPONSE_HEADER_FORMAT = '>II'
    WSA4000_DISCOVERY_VERSION = 1
    WSA5000_FORMAT = '16s16s20s'

    version = struct.unpack(RESPONSE_HEADER_FORMAT, response[:8])[1]
    if version == WSA4000_DISCOVERY_VERSION:
        return ('WSA4000', response[8:].split('\0', 1)[0], None)
    return tuple(v.rstrip('\0') for v in struct.unpack(WSA5000_FORMAT,
        response[8:]))

def discover_wsa(wait_time=0.125):
    import netifaces
    """
    This function returns a list that contains all of the RTSA's available
    on the local network

    :param wait_time: The total time to wait for responses in seconds
    :returns: Return a list of dicts (MODEL, SERIAL, FIRMWARE, IP) of all the  RTSA's available on the local network
    """

    cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    cs.setblocking(0)

    wsa_list = []

    ifaces = netifaces.interfaces()
    destinations = []
    for i in ifaces:
        addrs = netifaces.ifaddresses(i).get(netifaces.AF_INET, [])
        for a in addrs:
            if 'broadcast' in a:
                destinations.append(a['broadcast'])

    for d in destinations:
        # send query command to RTSA
        query_struct = DISCOVERY_QUERY
        cs.sendto(query_struct, (d, DISCOVERY_UDP_PORT))

    while True:
        ready, _, _ = select.select([cs], [], [], wait_time)
        if not ready:
            break
        data, (host, port) = cs.recvfrom(1024)

        model, serial, firmware = parse_discovery_response(data)
        wsa_list.append({"MODEL": model,
                        "SERIAL": serial,
                        "FIRMWARE": firmware,
                        "HOST": host})
    return  wsa_list


def cli_chooser():

    while True:
        # get list of boxes
        wsalist = discover_wsa(0.250)

        # calc column widths
        w_modelstring = 0
        w_serial = 0
        w_host = 0
        for wsa in wsalist:
            modelstring = "%s v%s" % (wsa["MODEL"], wsa["FIRMWARE"])

            if len(modelstring) > w_modelstring: w_modelstring = len(modelstring)
            if len(wsa["SERIAL"]) > w_serial: w_serial = len(wsa["SERIAL"])
            if len(wsa["HOST"]) > w_host: w_host = len(wsa["HOST"])

        # now print out the list
        fmt = "%%d) %%%ds - %%-%ds - %%%ds" % (w_host, w_modelstring, w_serial)
        index = 1
        for wsa in wsalist:
            modelstring = "%s v%s" % (wsa["MODEL"], wsa["FIRMWARE"])
            print fmt % (index, wsa["HOST"], modelstring, wsa["SERIAL"])
            index += 1
        print "r) Refresh"
        print "q) Abort"

        # get user input
        choice = raw_input("> ")
        if choice == "q":
            return None

        elif choice == 'r':
            # do nothing
            pass

        elif (int(choice) >= 1) and (int(choice) < (len(wsalist) + 1)):
            index = int(choice) - 1
            return wsalist[index]["HOST"]

        else:
            print "error: invalid selection: '%s'" % choice


# for backwards compatibility
WSA4000 = WSA
