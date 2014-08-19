from pyrf.config import SweepEntry, TriggerSettings, TRIGGER_TYPE_LEVEL, TRIGGER_TYPE_NONE, TriggerSettingsError
from pyrf.connectors.blocking import PlainSocketConnector
from pyrf.connectors.base import sync_async
from pyrf.vrt import vrt_packet_reader
from pyrf import windows_util
from pyrf import linux_util
from pyrf.devices.thinkrf_properties import wsa_properties

import struct
import socket
import select
import platform

DISCOVERY_UDP_PORT = 18331
_DISCOVERY_QUERY_CODE = 0x93315555
_DISCOVERY_QUERY_VERSION = 2
_DISCOVERY_QUERY_FORMAT = '>LL'
DISCOVERY_QUERY = struct.pack(_DISCOVERY_QUERY_FORMAT,
    _DISCOVERY_QUERY_CODE, _DISCOVERY_QUERY_VERSION)

class WSA(object):
    """
    Interface for WSA4000 and WSA5000

    :param connector: Connector object to use for SCPI/VRT connections,
        defaults to a new
        :class:`PlainSocketConnector <pyrf.connectors.blocking.PlainSocketConnector>`
        instance

    :meth:`connect() <pyrf.devices.thinkrf.WSA.connect>` must be called
    before other methods are used.

    .. note::

       The following methods will either block then return a result
       or if you passed a
       :class:`TwistedConnector <pyrf.connectors.twisted_async.TwistedConnector>`
       instance to the constructor they will immediately return a
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
        Inject the current speca state into the recording stream when
        the next capture is received.  Replaces previous data if not
        yet sent.
        """
        self.connector.inject_recording_state(state)

    @sync_async
    def connect(self, host):
        """
        connect to a wsa

        :param host: the hostname or IP to connect to
        """
        yield self.connector.connect(host)
        self.device_id = (yield self.scpiget(":*idn?"))
        self.properties = wsa_properties(self.device_id)

        self.fw_version = self.device_id.split(',')[-1]
        self.device_state = {}

    def disconnect(self):
        """
        close a connection to a wsa
        """
        self.connector.disconnect()
        if self.properties:
            del self.properties

    def scpiset(self, cmd):
        """
        Send a SCPI command.

        This is the lowest-level interface provided.
        Please see the Programmer's Guide for information about
        the commands available.

        :param cmd: the command to send
        :type cmd: str
        """
        self.connector.scpiset(cmd)

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
        return self.connector.scpiget(cmd)

    @sync_async
    def id(self):
        """
        Returns the WSA's identification information string.

        :returns: "<Manufacturer>,<Model>,<Serial number>,<Firmware version>"
        """
        yield self.scpiget(":*idn?")

    @sync_async
    def rfe_mode(self, mode=None):
        """
        This command sets or queries the WSA's Receiver Front End mode of
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
        This command sets or queries the WSA's current IQ path

        :param path: 'DIGITIZER', 'CONNECTOR', or None to query
        :returns: the current IQ path
        """

        if path is None:
            buf = yield self.scpiget(":OUTPUT:IQ:MODE?")
            path = buf.strip()
        else:
            self.scpiset(":OUTPUT:IQ:MODE %s" % path)
        yield path

    @sync_async
    def pll_reference(self, src=None):
        """
        This command sets or queries the WSA's PLL reference source

        :param src: 'INT', 'EXT', or None to query
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
        This command sets or queries the tuned center frequency of the WSA.

        :param freq: the new center frequency in Hz (0 - 10 GHz); None to query

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

        :param freq: the new frequency shift in Hz (0 - 125 MHz); None to query
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
    def gain(self, gain=None):
        """
        This command sets or queries RFE quantized gain configuration.
        The RF front end (RFE) of the WSA consists of multiple quantized
        gain stages. The gain corresponding to each user-selectable setting
        has been pre-calculated for either optimal sensitivity or linearity.
        The parameter defines the total quantized gain of the RFE.

        :param gain: 'high', 'medium', 'low' or 'vlow' to set; None to query
        :returns: the RF gain value
        """
        if gain is None:
            gain = yield self.scpiget("INPUT:GAIN:RF?")
        else:
            self.scpiset(":INPUT:GAIN:RF %s\n" % gain)

        yield gain.lower()

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
        This command sets or queries the RFE preselect filter selection.

        :param enable: True or False to set; None to query
        :returns: the RFE preselect filter selection state
        """
        if enable is None:
            enable = yield self.scpiget(":INPUT:FILTER:PRESELECT?")
            enable = bool(int(enable))
        else:
            self.scpiset(":INPUT:FILTER:PRESELECT %d" % int(enable))
        yield enable

    @sync_async
    def antenna(self, number=None):
        """
        This command selects and queries the active antenna port.

        :param number: 1 or 2 to set; None to query
        :returns: active antenna port
        """
        if number is None:
            number = yield self.scpiget(":INPUT:ANTENNA?")
            number = int(number)
        else:
            self.scpiset(":INPUT:ANTENNA %d" % number)
        yield number


    def reset(self):
        """
        Resets the WSA to its default settings. It does not affect
        the registers or queues associated with the IEEE mandated commands.
        """
        self.scpiset(":*rst")

    def abort(self):
        """
        This command will cause the WSA to stop the data capturing,
        whether in the manual trace block capture, triggering or sweeping
        mode.  The WSA will be put into the manual mode; in other
        words, process such as streaming, trigger and sweep will be
        stopped.  The capturing process does not wait until the end of a
        packet to stop, it will stop immediately upon receiving the command.
        """
        self.scpiset(":SYSTEM:ABORT")


    def flush(self):
        """
        This command clears the WSA's internal data storage buffer of
        any data that is waiting to be sent.  Thus, It is recommended that
        the flush command should be used when switching between different
        capture modes to clear up the remnants of packet.
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
        (i.e. Stream ID, Class ID, Timestamps, and trailer)  of 32-bit
        wide words.  However since the SPP must be a multiple of 16,
        the maximum is thus limited by 2**16 - 16.

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
        else:
            self.scpiset(":TRACE:BLOCK:PACKETS %s\n" % (packets,))
        yield number


    @sync_async
    def request_read_perm(self):
        """
        Acquire exclusive permission to read data from the WSA.

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
        PLL reference clock in the digital card.

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
        Read a single VRT packet from the WSA.
        """
        return vrt_packet_reader(self.connector.raw_read)

    def raw_read(self, num):
        """
        Raw read of VRT socket data from the WSA.

        :param num: the number of bytes to read
        :returns: bytes
        """
        return self.connector.raw_read(num)


    def sweep_add(self, entry):
        """
        Add an entry to the sweep list

        :param entry: the sweep entry to add
        :type entry: pyrf.config.SweepEntry
        """
        self.scpiset(":sweep:entry:new")
        if 'rfe_mode' in self.properties.SWEEP_SETTINGS:
            self.scpiset(":sweep:entry:mode %s" % (entry.rfe_mode))
        self.scpiset(":sweep:entry:freq:center %d, %d" % (entry.fstart, entry.fstop))
        self.scpiset(":sweep:entry:freq:step %d" % (entry.fstep))
        self.scpiset(":sweep:entry:freq:shift %d" % (entry.fshift))
        self.scpiset(":sweep:entry:decimation %d" % (entry.decimation))
        if 'antenna' in self.properties.SWEEP_SETTINGS:
            self.scpiset(":sweep:entry:antenna %d" % (entry.antenna))
        if 'gain' in self.properties.SWEEP_SETTINGS:
            self.scpiset(":sweep:entry:gain:rf %s" % (entry.gain))
        if 'attenuator' in self.properties.SWEEP_SETTINGS:
            self.scpiset(":sweep:entry:attenuator %s" % (
                1 if entry.attenuator else 0))
        self.scpiset(":sweep:entry:gain:if %d" % (entry.ifgain))
        self.scpiset(":sweep:entry:spp %d" % (entry.spp))
        self.scpiset(":sweep:entry:ppb %d" % (entry.ppb))
        self.scpiset(":sweep:entry:dwell %d,%d" %
            (entry.dwell_s, entry.dwell_us))
        self.scpiset(":sweep:entry:trigger:type %s" % (entry.trigtype))
        if entry.trigtype.lower() == 'level':
            self.scpiset(":sweep:entry:trigger:level %d, %d, %d" % (entry.level_fstart, entry.level_fstop, entry.level_amplitude))
        self.scpiset(":sweep:entry:save")

    @sync_async
    def sweep_read(self, index):
        """
        Read an entry from the sweep list.

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
        Set the number of iterations for the complete sweep list,

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
        self.scpiset(":SYSTEM:FLUSH")

    def stream_start(self, stream_id=None):
        """
        This command begins the execution of the stream capture.
        It will also initiate data capturing.  Data packets will
        be streamed (or pushed) from the WSA whenever data
        is available.

        :param stream_id: optional unsigned 32-bit stream identifier
        """
        self.scpiset(':TRACE:STREAM:START' +
            (' %d' % stream_id if stream_id else ''))

    def stream_stop(self):
        """
        This command stops the stream capture.  After receiving
        the command, the WSA system will stop when the current
        capturing VRT packet is completed.
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
    def attenuator(self, enable=None):
        """
        This command enables, disables or queries the WSA's RFE 20
        dB attenuation.

        :param enable: True or False to set; None to query
        :returns: the current attenuator state
        """
        if enable is None:
            enable = yield self.scpiget(":INPUT:ATTENUATOR?")
            enable = bool(int(enable))
        else:
            self.scpiset(":INPUT:ATTENUATOR %s" % (1 if enable else 0))
        yield enable

    @sync_async
    def errors(self):
        """
        Flush and return the list of errors from past commands
        sent to the WSA. An empty list is returned when no errors
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

    def apply_device_settings(self, settings):
        """
        This command takes a dict of device settings, and applies them to the 
        WSA

        :param settings: dict containing settings such as gain,antenna,etc
        """
        device_setting = {
            'freq': self.freq,
            'antenna': self.antenna,
            'gain': self.gain,
            'hdr_gain': self.hdr_gain,
            'ifgain': self.ifgain,
            'fshift': self.fshift,
            'decimation': self.decimation,
            'spp': self.spp,
            'ppb': self.ppb,
            'trigger': self.trigger,
            'attenuator': self.attenuator,
            'rfe_mode': self.rfe_mode,
            'iq_output_path': self.iq_output_path,
            'pll_reference': self.pll_reference,
            'trigger': self.trigger,
            }
        for k, v in settings.iteritems():
            #FIXME: Find more elegant way to do this
            if not k in self.device_state:
                self.device_state[k] = v
                device_setting[k](v)
            if not self.device_state[k] == v:
                self.device_state[k] = v
                device_setting[k](v)


def parse_discovery_response(response):
    """
    This function parses the WSA's raw discovery response

    :param response: The WSA's raw response to a discovery query
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
    """
    This function returns a list that contains all of the WSA's available
    on the local network

    :param wait_time: The total time to wait for responses in seconds
    :returns: Return a list of dicts (MODEL, SERIAL, FIRMWARE, IP) of all the WSA's
    available on the local network
    """

    cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    cs.setblocking(0)

    wsa_list = []

    if platform.system() == 'Windows':
        destinations = windows_util.get_broadcast_addresses()
    elif platform.system() == 'Linux':
        destinations = linux_util.get_broadcast_addresses()
    else:
        destinations = ['<broadcast>']

    for d in destinations:
        # send query command to WSA
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

# for backwards compatibility
WSA4000 = WSA

