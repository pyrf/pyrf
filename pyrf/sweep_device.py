import math
import random
from collections import namedtuple
import time
from pyrf.numpy_util import compute_fft
from pyrf.config import SweepEntry

class SweepStep(namedtuple('SweepStep', '''
        fcenter
        fstep
        fshift
        decimation
        points
        bins_skip
        bins_run
        bins_keep
        ''')):
    """
    Data structure used by SweepDevice for planning sweeps

    :param fcenter: starting center frequency in Hz
    :param fstep: frequency increment each step in Hz
    :param fshift: frequency shift in Hz
    :param decimation: decimation value
    :param points: samples to capture
    :param bins_skip: number of FFT bins to skip from left
    :param bins_run: number of usable FFT bins each step
    :param bins_keep: total number of bins to keep from all steps
    """
    __slots__ = []

    def to_sweep_entry(self, device, **kwargs):
        """
        Create a SweepEntry for device matching this SweepStep,

        extra parameters (gain, antenna etc.) may be provided as keyword
        parameters
        """
        if self.points > 32*1024:
            raise SweepDeviceError('large captures not yet supported')

        return SweepEntry(
            fstart=self.fcenter,
            fstop=min(self.fcenter + (self.steps + 0.5) * self.fstep,
                device.properties.MAX_TUNABLE),
            fstep=self.fstep,
            fshift=self.fshift,
            decimation=self.decimation,
            spp=self.points,
            ppb=1,
            **kwargs)

    @property
    def steps(self):
        return math.ceil(float(self.bins_keep) / self.bins_run)


    def trim(self, device, fstart, fstop):
        """
        Create a SweepStep that only includes steps within fstart to fstop
        or return None if no part of this SweepStep overlaps
        """
        if fstop <= fstart:
            return

        steps = self.steps
        bin_width = float(device.properties.FULL_BW
            ) / self.decimation / self.points
        start_centered = self.bins_skip - self.points / 2
        start_off = start_centered * bin_width - self.fshift
        stop_centered = start_centered + self.bins_run
        stop_off = stop_centered * bin_width - self.fshift

        start_step = math.floor((fstart - self.fcenter - start_off) / self.fstep)
        stop_step = steps + math.ceil(
            (fstop - self.fcenter - stop_off) / self.fstep)
        if steps <= start_step or stop_step <= 0:
            return

        last_bins_run = self.bins_keep % self.bins_run
        if steps - 1 == start_step and last_bins_run:
            # starting from last step special case: fstart might be
            # after the remaining samples
            last_stop_centered = start_centered + last_bins_run
            last_stop_off = last_stop_centered * bin_width - self.fshift
            last_stop = self.fcenter + steps * self.fstep + last_stop_off
            if last_stop <= fstart:
                return

        trim_left = max(0, start_step)
        trim_right = steps - min(steps, stop_step)
        return SweepStep(
            fcenter=self.fcenter + trim_left * self.fstep,
            fstep=self.fstep,
            fshift=self.fshift,
            decimation=self.decimation,
            points=self.points,
            bins_skip=self.bins_skip,
            bins_run=self.bins_run,
            bins_keep=self.bins_keep - (trim_left + trim_right) * self.bins_run,
            )


class SweepDeviceError(Exception):
    pass

class SweepDevice(object):
    """
    Virtual device that generates power levels from a range of
    frequencies by sweeping the frequencies with a real device
    and piecing together FFT results.

    :param real_device: device that will will be used for capturing data,
                        typically a :class:`pyrf.devices.thinkrf.WSA` instance.
    :param callback: callback to use for async operation (not used if
                     real_device is using a :class:`PlainSocketConnector`)
    """
    def __init__(self, real_device, async_callback=None):
        self.real_device = real_device
        self._sweep_id = random.randrange(0, 2**32-1) # don't want 2**32-1
        if hasattr(self.connector, 'vrt_callback'):
            if not async_callback:
                raise SweepDeviceError(
                    "async_callback required for async operation")
            # disable receiving data until we are expecting it
            self.connector.vrt_callback = None
        else:
            if async_callback:
                raise SweepDeviceError(
                    "async_callback not applicable for sync operation")
        self._prev_sweep_id = None
        self._trigger_sweep = False
        self._trigger_id = None
        self._trigger_data = {}
        self.async_callback = async_callback
        self.continuous = False
        self.context_bytes_received = 0
        self.data_bytes_received = 0
        self.data_bytes_processed = 0
        self.martian_bytes_discarded = 0
        self.past_end_bytes_discarded = 0
        self.fft_calculation_seconds = 0.0
        self.bin_collection_seconds = 0.0

    connector = property(lambda self: self.real_device.connector)

    def capture_power_spectrum(self,
            fstart, fstop, rbw, device_settings=None,
            triggers=None, continuous=False,
            min_points=128, max_points=8192):
        """
        Initiate a capture of power spectral density by
        setting up a sweep list and starting a single sweep.

        :param fstart: starting frequency in Hz
        :type fstart: float
        :param fstop: ending frequency in Hz
        :type fstop: float
        :param rbw: requested RBW in Hz (output RBW may be smaller than
                    requested)
        :type rbw: float
        :param device_settings: antenna, gain and other device settings
        :type dict:
        :param triggers: list of :class:`TriggerSettings` instances or None
        :param continuous: async continue after first sweep
        :type continuous: bool
        :param min_points: smallest number of points per capture from real_device
        :type min_points: int
        :param max_points: largest number of points per capture from real_device
                           (due to decimation limits points returned may be larger)
        :type max_points: int

        When triggers are provided nothing will be captured until one of the
        triggers is satisfied. The trigger data received is combined with a full
        sweep before being returned.
        """
        if continuous and not self.async_callback:
            raise SweepDeviceError(
                "continuous mode only applies to async operation")
        self.device_settings = device_settings
        self.continuous = continuous

        self.real_device.abort()
        self.real_device.flush()
        self.real_device.request_read_perm()

        self.fstart, self.fstop, self.plan = plan_sweep(self.real_device,
            fstart, fstop, rbw, min_points, max_points)

        result = self._perform_trigger_sweep(triggers)
        if result == 'async waiting':
            return

        return self._perform_full_sweep()


    def _perform_trigger_sweep(self, triggers):
        entries = []
        if not triggers:
            return
        for t in triggers:
            if t.trigtype != 'LEVEL':
                raise SweepDeviceError('only level triggers supported')
            tplan = trim_sweep_plan(self.real_device,
                self.plan, t.fstart, t.fstop)
            for ss in tplan:
                entries.append(ss.to_sweep_entry(self.real_device,
                    dwell_us=1,
                    trigtype=t.trigtype,
                    level_fstart=t.fstart,
                    level_fstop=t.fstop,
                    level_amplitude=t.amplitude,
                    **self.device_settings))
        if not entries:
            return

        if self.async_callback:
            self.connector.vrt_callback = self._vrt_receive
            self._start_sweep(entries, trigger=True)
            return 'async waiting'
        assert not self._trigger_data
        self._start_sweep(entries, trigger=True)
        while not self._trigger_data:
            result = self._vrt_receive(self.real_device.read())


    def _perform_full_sweep(self):
        entries = []
        for ss in self.plan:
            entries.append(ss.to_sweep_entry(self.real_device,
                **self.device_settings))

        if self.async_callback:
            if not self.plan:
                self.async_callback(self.fstart, self.fstop, [])
                return
            self.connector.vrt_callback = self._vrt_receive
            self._start_sweep(entries)
            return

        if not self.plan:
            return (self.fstart, self.fstop, [])
        self._start_sweep(entries)
        result = None
        while result is None:
            result = self._vrt_receive(self.real_device.read())
        return result

    def _start_sweep(self, entries, trigger=False):
        self.real_device.abort()
        self.real_device.flush()
        self.real_device.sweep_clear()
        assert entries, "starting sweep with no sweep entries"
        for e in entries:
            self.real_device.sweep_add(e)
        self._prev_sweep_id = self._sweep_id
        self._sweep_id = (self._sweep_id + 1) & (2**32 - 1)
        self._vrt_context = {}
        self._ss_index = 0
        self._ss_received = 0
        self.bins = []
        self.real_device.sweep_iterations(
            0 if trigger or self.continuous else 1)
        self.real_device.sweep_start(self._sweep_id)
        self._trigger_sweep = trigger
        if trigger:
            self._trigger_id = self._sweep_id

    def _vrt_receive(self, packet):
        packet_bytes = packet.size * 4

        if packet.is_context_packet():
            self._vrt_context.update(packet.fields)
            self.context_bytes_received += packet_bytes
            return

        self.data_bytes_received += packet_bytes
        sweep_id = self._vrt_context.get('sweepid')
        if sweep_id not in (self._sweep_id, self._trigger_id):
            if sweep_id == self._prev_sweep_id:
                self.past_end_bytes_discarded += packet_bytes
            else:
                self.martian_bytes_discarded += packet_bytes
            return # not our data
        # WORKAROUND for 5K not always sending reflevel
        if 'reflevel' not in self._vrt_context:
            self._vrt_context['reflevel'] = 0
        assert 'reflevel' in self._vrt_context, (
            "missing required context, sweep failed")

        freq = self._vrt_context['rffreq']
        if self._trigger_sweep or sweep_id == self._trigger_id:
            self._trigger_data[freq] = packet
            if self._trigger_sweep and self.async_callback:
                self._perform_full_sweep()
            return

        if self._ss_index is None:
            self.past_end_bytes_discarded += packet_bytes
            return # more data than we asked for

        fft_start_time = time.time()
        # replace with trigger data when available
        packet = self._trigger_data.get(freq, packet)
        pow_data = compute_fft(self.real_device, packet, self._vrt_context)
        # collect and compute bins
        collect_start_time = time.time()
        ss = self.plan[self._ss_index]
        take = min(ss.bins_run, ss.bins_keep - self._ss_received)
        self.bins.extend(pow_data[ss.bins_skip:ss.bins_skip + take])
        self._ss_received += take
        collect_stop_time = time.time()

        self.fft_calculation_seconds += collect_start_time - fft_start_time
        self.bin_collection_seconds += collect_stop_time - collect_start_time
        self.data_bytes_processed += take * 4

        if self._ss_received < ss.bins_keep:
            return

        self._ss_received = 0
        self._ss_index += 1
        if self._ss_index < len(self.plan):
            return

        # done the complete sweep
        # XXX: in case sweep_iterations() does not work
        if not self.continuous:
            self._ss_index = None
            self._trigger_data = {}
            self.real_device.abort()
            self.real_device.flush()

        if self.async_callback:
            self.real_device.vrt_callback = None
            self.async_callback(self.fstart, self.fstop, self.bins)
            if self.continuous:
                self._ss_index = 0
                self._ss_received = 0
                self.bins = []
            return
        return (self.fstart, self.fstop, self.bins)



def plan_sweep(device, fstart, fstop, rbw, min_points=128, max_points=8192):
    """
    :param device: a device class or instance such as
                   :class:`pyrf.devices.thinkrf.WSA`
    :param fstart: starting frequency in Hz
    :type fstart: float
    :param fstop: ending frequency in Hz
    :type fstop: float
    :param rbw: requested RBW in Hz (output RBW may be smaller than requested)
    :type rbw: float
    :param min_points: smallest number of points per capture
    :type min_points: int
    :param max_points: largest number of points per capture (due to
                       decimation limits points returned may be larger)
    :type max_points: int

    The following device properties are used in planning the sweep:

    device.properties.FULL_BW
      full width of the filter in Hz
    device.properties.USABLE_BW
      usable portion before filter drop-off at edges in Hz
    device.properties.MIN_TUNABLE
      the lowest valid center frequency for arbitrary tuning in Hz,
      0(DC) is always assumed to be available for direct digitization
    device.properties.MAX_TUNABLE
      the highest valid center frequency for arbitrart tuning in Hz
    device.properties.MIN_DECIMATION
      the lowest valid decimation value above 1, 1(no decimation) is
      assumed to always be available
    device.properties.MAX_DECIMATION
      the highest valid decimation value, only powers of 2 will be used
    device.properties.DECIMATED_USABLE
      the fraction decimated output containing usable data, float < 1.0
    device.properties.DC_OFFSET_BW
      the range of frequencies around center that may be affected by
      a DC offset and should not be used

    :returns: (actual fstart, actual fstop, list of SweepStep instances)

    The caller would then use each of these tuples to do the following:

    1. The first 5 values are used for a single capture or single sweep
    2. An FFT is run on the points returned to produce bins in the linear
       domain
    3. bins[bins_skip:bins_skip + bins_run] are selected
    4. take logarithm of output bins and appended to the result
    5. for sweeps repeat from 2 until the sweep is complete
    6. bins_keep is the total number of selected bins to keep; for
       single captures bins_run == bins_keep
    """
    prop = device.properties
    out = []
    usable2 = prop.USABLE_BW / 2.0
    dc_offset2 = prop.DC_OFFSET_BW / 2.0

    # FIXME: truncate to left-hand sweep area for now
    fstart = max(prop.MIN_TUNABLE - usable2, fstart)
    fstop = min(prop.MAX_TUNABLE - dc_offset2, fstop)

    if fstop <= fstart:
        return (fstart, fstart, [])

    points = prop.FULL_BW / rbw
    points = max(min_points, 2 ** math.ceil(math.log(points, 2)))

    decimation = 1
    ideal_decimation = 2 ** math.ceil(math.log(float(points) / max_points, 2))
    min_decimation = max(2, prop.MIN_DECIMATION)
    max_decimation = 2 ** math.floor(math.log(prop.MAX_DECIMATION, 2))
    if max_points < points and min_decimation <= ideal_decimation:
        decimation = min(max_decimation, ideal_decimation)
        points /= decimation
        decimated_bw = prop.FULL_BW / decimation
        decimation_edge_bins = math.ceil(points * prop.DECIMATED_USABLE / 2.0)
        decimation_edge = decimation_edge_bins * decimated_bw / points

    bin_size = prop.FULL_BW / decimation / float(points)

    # there are three regions that need to be handled differently
    # region 0: direct digitization / "VLOW band"
    if fstart < prop.MIN_TUNABLE - usable2:
        raise NotImplemented # yet

    # region 1: left-hand sweep area
    if prop.MIN_TUNABLE - usable2 <= fstart:
        if decimation == 1:
            left_edge = prop.FULL_BW / 2.0 - usable2
            left_bin = math.ceil(left_edge / bin_size)
            fshift = left_bin * bin_size - left_edge
            usable_bins = (usable2 - dc_offset2 - fshift) // bin_size
        else:
            left_bin = decimation_edge_bins
            fshift = usable2 + decimation_edge - (decimated_bw / 2.0)
            usable_bins = min(points - (decimation_edge_bins * 2),
                (usable2 - dc_offset2) // bin_size)

        usable_bw = usable_bins * bin_size

        fcenter = fstart + usable2
        # FIXME: fstop not being updated here
        max_steps = math.floor((prop.MAX_TUNABLE - fstart) / usable_bw)
        bins_keep = min(round((fstop - fstart) / bin_size),
            max_steps * usable_bins)
        sweep_steps = math.ceil(bins_keep / usable_bins)
        out.append(SweepStep(
            fcenter=fcenter,
            fstep=usable_bw,
            fshift=fshift,
            decimation=decimation,
            points=int(points),
            bins_skip=int(left_bin),
            bins_run=int(min(usable_bins, bins_keep)),
            bins_keep=int(bins_keep),
            ))

    # region 2: right-hand edge
    if prop.MAX_TUNABLE - dc_offset2 < fstop:
        raise NotImplemented # yet

    return (fstart, fstop, out)


def trim_sweep_plan(device, plan, fstart, fstop):
    """
    :param device: a device class or instance such as
                   :class:`pyrf.devices.thinkrf.WSA`
    :param plan: list of :class:`SweepStep` instances
    :param fstart: starting frequency in Hz
    :type fstart: float
    :param fstop: ending frequency in Hz
    :type fstop: float

    produce a new sweep plan consisting of captures from the passed
    sweep plan that overlap with the range fstart to fstop.
    """

    trimmed = (ss.trim(device, fstart, fstop) for ss in plan)
    return [t for t in trimmed if t]

