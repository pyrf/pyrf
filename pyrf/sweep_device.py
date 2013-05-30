import math
from collections import namedtuple

SweepStep = namedtuple('SweepStep', '''
    fstart
    fstop
    fstep
    fshift
    decimation
    points
    bins_skip
    bins_run
    bins_keep
    ''')

def plan_sweep(device, fstart, fstop, bins, min_points=128):
    """
    :param device: a device class or instance such as
                   :class:`pyrf.devices.thinkrf.WSA4000`
    :param fstart: starting frequency in Hz
    :type fstart: float
    :param fstop: ending frequency in Hz
    :type fstop: float
    :param bins: FFT bins requested (number produced likely more)
    :type bins: int

    The following device attributes are used in planning the sweep:

    device.FULL_BW
      full width of the filter in Hz
    device.USABLE_BW
      usable portion before filter drop-off at edges in Hz
    device.MIN_TUNABLE
      the lowest valid center frequency for arbitrary tuning in Hz,
      0(DC) is always assumed to be available for direct digitization
    device.MAX_TUNABLE
      the highest valid center frequency for arbitrart tuning in Hz
    device.MIN_DECIMATION
      the lowest valid decimation value above 1, 1(no decimation) is
      assumed to always be available
    device.MAX_DECIMATION
      the highest valid decimation value, only powers of 2 will be used
    device.DECIMATED_USABLE
      the fraction decimated output containing usable data, float < 1.0
    device.DC_OFFSET_BW
      the range of frequencies around center that may be affected by
      a DC offset and should not be used

    :returns: a list of SweepStep namedtuples:

       (fstart, fstop, fstep, fshift, decimation, points, 
       bins_skip, bins_run, bins_keep)

    The caller would then use each of these tuples to do the following:

    1. The first 6 values are used for a single capture or single sweep
    2. An FFT is run on the points returned to produce bins in the linear
       domain
    3. bins[bins_skip:bins_skip + bins_run] are selected
    4. take logarithm of output bins and appended to the result
    5. for sweeps repeat from 2 until the sweep is complete
    6. bins_keep is the total number of selected bins to keep; for
       single captures bins_run == bins_keep
    """
    out = []
    usable2 = device.USABLE_BW / 2.0
    dc_offset2 = device.DC_OFFSET_BW / 2.0

    ideal_bin_size = (fstop - fstart) / float(bins)
    points = device.FULL_BW / ideal_bin_size
    points = max(min_points, 2 ** math.ceil(math.log(points, 2)))
    bin_size = device.FULL_BW / float(points)

    left_edge = device.FULL_BW / 2.0 - usable2
    left_bin = math.ceil(left_edge / bin_size)
    fshift = left_bin * bin_size - left_edge

    usable_bins = int((usable2 - dc_offset2 - fshift) // bin_size)
    usable_bw = usable_bins * bin_size

    # there are three regions that need to be handled differently
    # region 0: direct digitization / "VLOW band"
    if fstart < device.MIN_TUNABLE - usable2:
        raise NotImplemented # yet

    # region 1: left-hand sweep area
    if fstart >= device.MIN_TUNABLE - usable2:
        start = fstart + usable2
        step = usable_bw
        bins_keep = int(round((fstop - fstart) / bin_size))
        sweep_steps = -((-bins_keep) // usable_bins)
        stop = start + step * (sweep_steps - 0.5)
        out.append(SweepStep(
            fstart=start,
            fstop=stop,
            fstep=step,
            fshift=fshift,
            decimation=1,
            points=points,
            bins_skip=left_bin,
            bins_run=usable_bins,
            bins_keep=int(round((fstop - fstart) / bin_size)),
            ))

    # region 2: right-hand edge
    if fstop > device.MAX_TUNABLE - dc_offset2:
        raise NotImplemented # yet

    return out
