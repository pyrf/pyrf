
def plan_sweep(device, fstart, fstop, bin_size):
    """
    :param device: a device class or instance such as
                   :class:`pyrf.devices.thinkrf.WSA4000`
    :param fstart: starting frequency in Hz
    :param fstop: ending frequency in Hz
    :param bin_size: FFT bin size in Hz

    This function generates a list of tuples:
        (freq, fshift, decimation, points, bins_skip, bins_run, bins_out)

    freq is an integer for single captures or a tuple for sweeps:
        (sweep fstart, sweep shift, sweep capture count) 
    """
