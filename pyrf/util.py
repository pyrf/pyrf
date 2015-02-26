import math

from pyrf.vrt import I_ONLY
from ast import literal_eval
def read_data_and_context(dut, points=1024):
    """
    Initiate capture of one data packet, wait for and return data packet
    and collect preceeding context packets.

    :returns: (data_pkt, context_values)

    Where context_values is a dict of {field_name: value} items from
    all the context packets received.
    """
    # capture 1 packet
    dut.capture(points, 1)

    return collect_data_and_context(dut)

def collect_data_and_context(dut):
    """
    Wait for and return data packet and collect preceeding context packets.
    """
    context_values = {}
    # read until I get 1 data packet
    while not dut.eof():
        pkt = dut.read()

        if pkt.is_data_packet():
            break

        context_values.update(pkt.fields)

    return pkt, context_values

# avoid breaking pyrf 0.2.x examples:
read_data_and_reflevel = read_data_and_context


def compute_usable_bins(dut_prop, rfe_mode, points, decimation, fshift):
    """
    Return a list of usable bin ranges for the given capture configuration
    in the form [(start, run), ...] where start is a bin offset from the
    left and run is a number of usable bins.
    """
    if rfe_mode in ('SH', 'SHN') and decimation > 1:
        pass_band_center = dut_prop.PASS_BAND_CENTER['DEC_' + rfe_mode]
        full_bw = (dut_prop.FULL_BW['DEC_' + rfe_mode] / decimation)
    else:
        pass_band_center = dut_prop.PASS_BAND_CENTER[rfe_mode]
        full_bw = dut_prop.FULL_BW[rfe_mode] / decimation

    if decimation > 1:
        usable_bw = full_bw * dut_prop.DECIMATED_USABLE
    else:
        usable_bw = dut_prop.USABLE_BW[rfe_mode]

    pass_band_center += fshift / full_bw
    start0 = int((pass_band_center - float(usable_bw) / full_bw / 2)
        * points)

    run0 = int(points * float(usable_bw) / full_bw)
    usable_bins = [(start0, run0)]

    for i, (start, run) in enumerate(usable_bins):
        if start < 0:
            run += start
            start = 0
            usable_bins[i] = (start, run)

    if decimation == 1 and dut_prop.DEFAULT_SAMPLE_TYPE.get(rfe_mode) == I_ONLY:
        # we're getting only 1/2 the bins
        usable_bins = [(x/2, y/2) for x, y in usable_bins]

    # XXX usable bins for SH + fshift aren't correct yet, so show everything
    if rfe_mode in ('SH', 'SHN') and fshift:
        usable_bins = [(0, points)]

    return usable_bins


def adjust_usable_fstart_fstop(dut_prop, rfe_mode, points, decimation,
        freq, spec_inv, usable_bins):
    """
    Return an adjusted usable_bins array and the real fstart and fstop
    based on spectral inversion.
    """

    if rfe_mode in ('SH', 'SHN') and decimation > 1:
        pass_band_center = dut_prop.PASS_BAND_CENTER['DEC_' + rfe_mode]
        full_bw = (dut_prop.FULL_BW['DEC_' + rfe_mode] / decimation)
    else:
        pass_band_center = dut_prop.PASS_BAND_CENTER[rfe_mode]
        full_bw = dut_prop.FULL_BW[rfe_mode] / decimation

    offset = full_bw * (0.5 - pass_band_center)
    if spec_inv:
        offset = -offset
    fstart = freq - full_bw / 2.0 + offset
    fstop = freq + full_bw / 2.0 + offset

    # XXX here we "know" that bins = samples/2
    if spec_inv and rfe_mode in ('SH', 'SHN'):
        [(start, run)] = usable_bins
        start = points / 2 - start - run
        usable_bins = [(start, run)]

    return usable_bins, fstart, fstop


def trim_to_usable_fstart_fstop(bins, usable_bins, fstart, fstop):
    """
    Returns (trimmed bins, trimmed usable_bins,
    adjusted fstart, adjusted fstop)
    """
    left_bin = usable_bins[0][0]
    right_bin = usable_bins[-1][0] + usable_bins[-1][1]
    span = fstop - fstart

    adj_fstart = float(span) * left_bin / len(bins) + fstart
    adj_fstop = float(span) * right_bin / len(bins) + fstart
    trim_bins = [(s - left_bin, r) for (s, r) in usable_bins]

    return bins[left_bin:right_bin], trim_bins, adj_fstart, adj_fstop

def decode_config_type(config_str, str_type):
    """
    returns config_str value based on str_type
    """

    if isinstance(str_type, bool):
        value = (config_str == 'True')
    elif isinstance(str_type, int):
        value = int(config_str)
    elif  isinstance(str_type, float):
        value = float(config_str)
    elif  isinstance(str_type, long):
        value = long(config_str)
    elif  isinstance(str_type, str):
        value = config_str
    elif isinstance(str_type, list):
            value = literal_eval(config_str)

    elif isinstance(str_type, tuple):
        # for tuple, remove type, then remove brackets, then split by ',' and final convert to float tuple
        try:
            value = tuple([float(i) for i in (config_str[1:-1].split(','))])
        except ValueError:
            value = tuple([int(i) for i in (config_str[1:-1].split(','))])
    else:
        value = config_str
    return value