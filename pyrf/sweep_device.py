
def plan_sweep(device, fstart, fstop, bins):
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

    device.

    This function generates a list of tuples:

      (fstart, fstop, fstep, fshift, decimation, points, 
       bins_skip, bins_run, bins_reduce)

    The caller would then use each of these tuples to do the following:

    1. The first 6 values are used for a single capture or single sweep
    2. An FFT is run on the points returned to produce bins in the linear
       domain
    3. bins[bins_skip:bins_skip + bins_run] are selected
    4. bins_reduce selected bins are summed to produce output bins: 
       np.sum(selected_bins.reshape((-1, bins_reduce)), axis=1)
    5. take logarithm of output bins and appended to the result
    6. for sweeps (fstart != fstop) repeat from 2 until the sweep is complete
    """

