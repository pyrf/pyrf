import math
import random
from collections import namedtuple
import time

import numpy as np

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
        bins_pass
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
    :param bins_pass: number of bins from first step to discard from left
    :param bins_keep: total number of bins to keep from all steps
    """
    __slots__ = []

    def to_sweep_entry(self, device, rfe_mode, **kwargs):
        """
        Create a SweepEntry for device matching this SweepStep,

        extra parameters (gain, antenna etc.) may be provided as keyword
        parameters
        """
        # FIXME: this maximum depends on rfe_mode
        if self.points > 32*1024:
            raise SweepDeviceError('large captures not yet supported')

        s = SweepEntry(
            fstart=self.fcenter,
            fstop=min(self.fcenter + (self.steps + 0.5) * self.fstep,
                device.properties.MAX_TUNABLE[rfe_mode]),
            fstep=self.fstep,
            fshift=self.fshift,
            decimation=self.decimation,
            spp=self.points,
            ppb=1,
            rfe_mode=rfe_mode,
            **kwargs)
        return s

    @property
    def steps(self):
        return math.ceil(float(
            self.bins_keep + self.bins_pass) / self.bins_run)




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
        if real_device.async_connector():
            if not async_callback:
                raise SweepDeviceError(
                    "async_callback required for async operation")
            # disable receiving data until we are expecting it
            real_device.set_async_callback(None)
        else:
            if async_callback:
                raise SweepDeviceError(
                    "async_callback not applicable for sync operation")
        self._prev_sweep_id = None
        self.async_callback = async_callback
        self.continuous = False
        self.context_bytes_received = 0
        self.data_bytes_received = 0
        self.data_bytes_processed = 0
        self.martian_bytes_discarded = 0
        self.past_end_bytes_discarded = 0
        self.fft_calculation_seconds = 0.0
        self.bin_collection_seconds = 0.0

    def capture_power_spectrum(self,
            fstart, fstop, rbw,
            device_settings=None,
            mode='ZIF',
            continuous=False,
            min_points=32):
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
        :param mode: sweep mode, 'ZIF left band', 'ZIF' or 'SH'
        :type mode: string
        :param continuous: async continue after first sweep
        :type continuous: bool
        :param min_points: smallest number of points per capture from real_device
        :type min_points: int
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
            fstart, fstop, rbw, mode, min_points)
        self.rfe_mode = 'SH' if mode == 'SH' else 'ZIF'

        self.sweep_segments = []
        for ss in self.plan:
            k = ss.bins_keep
            seg = min(k, ss.bins_run - ss.bins_pass)
            while True:
                self.sweep_segments.append(seg)
                k -= seg
                if k <= 0:
                    break
                seg = min(ss.bins_run, k)

        return self._perform_full_sweep()

    def _perform_full_sweep(self):
        entries = []
        for ss in self.plan:
            entries.append(ss.to_sweep_entry(self.real_device,
                self.rfe_mode,
                **self.device_settings))

        if self.async_callback:
            if not self.plan:
                self.async_callback(self.fstart, self.fstop, [])
                return
            self.real_device.set_async_callback(self._vrt_receive)
            self._start_sweep(entries)
            return

        if not self.plan:
            return (self.fstart, self.fstop, [])
        self._start_sweep(entries)
        result = None
        while result is None:
            result = self._vrt_receive(self.real_device.read())
        return result

    def _start_sweep(self, entries):
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
        self.bin_arrays = []
        self.real_device.sweep_iterations(0 if self.continuous else 1)
        self.real_device.sweep_start(self._sweep_id)

    def _vrt_receive(self, packet):
        packet_bytes = packet.size * 4

        if packet.is_context_packet():
            self._vrt_context.update(packet.fields)
            self.context_bytes_received += packet_bytes
            return

        self.data_bytes_received += packet_bytes
        sweep_id = self._vrt_context.get('sweepid')
        if sweep_id != self._sweep_id:
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

        if self._ss_index is None:
            self.past_end_bytes_discarded += packet_bytes
            return # more data than we asked for

        fft_start_time = time.time()
        pow_data = compute_fft(self.real_device, packet, self._vrt_context)
        # collect and compute bins
        collect_start_time = time.time()
        ss = self.plan[self._ss_index]
        pass_now = 0 if self._ss_received else ss.bins_pass
        take = min(ss.bins_run - pass_now, ss.bins_keep - self._ss_received)
        start = ss.bins_skip + pass_now

        # adjust for not-centered pass band
        pbc = self.real_device.properties.PASS_BAND_CENTER[self.rfe_mode]
        if pbc != 0.5:
            offset = int(len(pow_data) * (pbc - 0.5))
            if packet.spec_inv:
                offset = -offset
            start += offset

        self.bin_arrays.append(pow_data[start:start + take])
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
            self.real_device.abort()
            self.real_device.flush()

        self.bins = np.concatenate(self.bin_arrays)
        if self.async_callback:
            self.real_device.vrt_callback = None
            self.async_callback(self.fstart, self.fstop, self.bins)
            if self.continuous:
                self._ss_index = 0
                self._ss_received = 0
                self.bins = []
            return
        return (self.fstart, self.fstop, self.bins)



def plan_sweep(device, fstart, fstop, rbw, mode, min_points=32):
    """
    :param device: a device class or instance such as
                   :class:`pyrf.devices.thinkrf.WSA`
    :param fstart: starting frequency in Hz
    :type fstart: float
    :param fstop: ending frequency in Hz
    :type fstop: float
    :param rbw: requested RBW in Hz (output RBW may be smaller than requested)
    :type rbw: float
    :param mode: sweep mode, 'ZIF left band', 'ZIF' or 'SH'
    :type mode: string
    :param min_points: smallest number of points per capture
    :type min_points: int

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
    device.properties.DC_OFFSET_BW
      the range of frequencies around center that may be affected by
      a DC offset and should not be used
    device.properties.TUNING_RESOLUTION
      the smallest tuning increment for fcenter and fstep

    :returns: (actual fstart, actual fstop, list of SweepStep instances)

    The caller would then use each of these tuples to do the following:

    1. The first 5 values are used for a single capture or single sweep
    2. An FFT is run on the points returned to produce bins in the linear
       domain
    3. bins[bins_skip:bins_skip + bins_run] are selected
    4. take logarithm of output bins and appended to the result
    5. for sweeps repeat from 2 until the sweep is complete
    6. bins_pass is the number of selected bins to skip from the first
       capture only
    7. bins_keep is the total number of selected bins to keep; for
       single captures bins_run == bins_keep
    """
    assert mode in ('ZIF left band', 'ZIF', 'SH')
    rfe_mode = 'SH' if mode == 'SH' else 'ZIF'
    prop = device.properties
    out = []
    usable2 = prop.USABLE_BW[rfe_mode] / 2.0
    dc_offset2 = prop.DC_OFFSET_BW / 2.0
    full_bw = prop.FULL_BW[rfe_mode]

    fstart = max(prop.MIN_TUNABLE[rfe_mode] - usable2, fstart)
    fstop = min(prop.MAX_TUNABLE[rfe_mode] + (
        -dc_offset2 if mode == 'ZIF left band' else usable2), fstop)

    if fstop <= fstart:
        return (fstart, fstart, [])

    points = full_bw / rbw
    points = int(max(min_points, 2 ** math.ceil(math.log(points, 2))))

    decimation = 1
    bin_size = float(full_bw) / decimation / points

    left_edge = full_bw / 2.0 - usable2
    left_bin = math.ceil(left_edge / bin_size)
    fshift = 0 # always preferred
    wasted_left = left_bin * bin_size - left_edge
    if mode == 'ZIF left band':
        usable_bins = (usable2 - dc_offset2 - wasted_left) // bin_size
    else:
        usable_bins = (usable2 - wasted_left) // bin_size * 2

    # step_size is limited by tuning resolution. usable_bw is limited by
    # bin_size. They won't be exactly equal, but try our best
    step_size = max(1, (usable_bins * bin_size // prop.TUNING_RESOLUTION)
        ) * prop.TUNING_RESOLUTION
    # reduce usable_bins to match tuning resolution increment
    usable_bins = int(max(1, min(usable_bins, round(step_size / bin_size))))
    usable_bw = usable_bins * bin_size

    # start at the next tuning resolution increment left of ideal start
    fcenter = math.floor((fstart + usable2 - wasted_left)
        / prop.TUNING_RESOLUTION) * prop.TUNING_RESOLUTION
    fcenter = max(fcenter, prop.MIN_TUNABLE[rfe_mode])
    bins_pass = int(round((fstart - (fcenter - usable2 + wasted_left))
        / bin_size))
    # we now have our actual fstart
    fstart = fcenter - bin_size * (points / 2 - left_bin - bins_pass) - fshift

    # calculate steps and bins
    step_limit = (prop.MAX_TUNABLE[rfe_mode] - fcenter) // step_size
    if mode == 'ZIF':
        right0 = fcenter + usable2 - wasted_left
    else:  # 'ZIF left band'
        right_edge = usable2 - usable_bw - wasted_left
        right0 = fcenter - right_edge
    steps = max(1, 1 + math.ceil((float(fstop) - right0) / step_size))
    if steps <= step_limit:
        right_bins = round(usable_bins * ((float(fstop) - right0) %
            step_size / step_size))
        if not right_bins:
            right_bins = usable_bins
        bins_keep = usable_bins * (steps - 1) - bins_pass + right_bins
    else:
        steps = step_limit
        bins_keep = usable_bins * steps - bins_pass

    # we now have our actual fstop
    fstop = ((bins_keep + bins_pass - 1) // usable_bins) * step_size + (
        (bins_keep + bins_pass - 1) % usable_bins + 1) * bin_size + fstart

    # adjust points for I-only data
    if mode == 'SH':
        points *= 2

    assert fcenter % prop.TUNING_RESOLUTION == 0, fcenter
    assert step_size > 0 and step_size % prop.TUNING_RESOLUTION == 0, step_size
    assert decimation > 0 and int(decimation) == decimation, decimation
    assert points > 0 and int(points) == points, points
    assert left_bin > 0 and int(left_bin) == left_bin, left_bin
    assert usable_bins > 0 and int(usable_bins) == usable_bins, usable_bins
    out.append(SweepStep(
        fcenter=fcenter,
        fstep=step_size,
        fshift=fshift,
        decimation=int(decimation),
        points=int(points),
        bins_skip=int(left_bin),
        bins_run=int(usable_bins),
        bins_pass=int(bins_pass),
        bins_keep=int(bins_keep),
        ))

    return (fstart, fstop, out)


