import math

from pyrf.vrt import I_ONLY
from ast import literal_eval
from pyrf.numpy_util import  compute_fft
import numpy as np
def capture_spectrum(dut, rbw = None, average=1):
    """
    Returns the spectral data, and the start frequency, stop frequency corresponding to the 
    WSA's current configuration
    :param rbw: rbw of spectral capture (Hz) (will round to nearest native RBW)
    :param average: number of capture iterations
    :returns: (fstart, fstop, pow_data)
    where pow_data is a list
    """
    
    # grab mode/decimation
    mode = dut.rfe_mode()
    dec = dut.decimation()
    bandwidth = dut.properties.FULL_BW[mode]

    # calculate points if RBW is given
    if rbw is not None:
        # calculate nearest rbw available
        req_points = bandwidth / rbw
        try:
            points =  dut.properties.SAMPLE_SIZES[np.argmin(np.abs(np.subtract(dut.properties.SAMPLE_SIZES,int(req_points)))) + 1]
        except IndexError:
            points = dut.properties.SAMPLE_SIZES[-1]
        # determine if multiple packets per block are required
        if points > dut.properties.MAX_SPP:
            samples = dut.properties.MAX_SPP
            packets = points / dut.properties.MAX_SPP
        else:
            samples = points
            packets = 1
        dut.spp(samples)
        dut.ppb(packets)
    # if no rbw requested, use current point
    else:
        samples = dut.spp()
        packets = dut.ppb()
        points = samples * packets
    rbw = bandwidth / points
    # calculate the usable bins
    freq = dut.freq()
    fshift = dut.fshift()
    fstart = freq - bandwidth / 2
    fstop = freq + bandwidth/ 2
    usable_bins = compute_usable_bins(dut.properties, mode, points, dec, fshift)

    total_pow = []
    for v in range(average):
        # read data
        for p in range(packets):
            if p == 0:
                data, context = read_data_and_context(dut, samples)

            else:
                d, c = read_data_and_context(dut, samples)
                data.data.np_array = np.concatenate([data.data.np_array, d.data.np_array])
        
        # adjust fstart and fstop based on the spectral inversion
        usable_bins, fstart, fstop = adjust_usable_fstart_fstop(
            dut.properties,
            mode,
            points,
            dec,
            freq,
            data.spec_inv,
            usable_bins)
        # compute fft
        pow_data = compute_fft(dut, data, context)
        if not len(total_pow):
            total_pow = pow_data
        else:
            total_pow = np.add(total_pow, pow_data)
    pow_data = total_pow / average
    # trim FFT
    pow_data, usable_bins, fstart, fstop = trim_to_usable_fstart_fstop(pow_data, 
                                                                    usable_bins,  
                                                                    fstart,  
                                                                    fstop)

    return (fstart, fstop, pow_data)

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
    if rfe_mode != 'ZIF':
        run0 = int(points * float(usable_bw) / full_bw)
        usable_bins = [(start0, run0)]
    else:
        run0 = int(points * float(usable_bw) / full_bw)
        start1 = start0 + int(run0 / 2 ) + 2
        usable_bins = [(start0, start1 - start0 - 3),
            (start1, run0 - (start1 - start0))]

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
    
def find_saturation(freq, saturation_values, attenuation):
    """
    return a saturation value based on the frequency and amount of attenuation
    :param freq: the freq of interest
    :param saturation_values: a dict containing the saturation values (keys are frequencies)
    :param attenuation: the amount of attenuation applied
    :returns: the closest saturation value corresponding to the frequency
    """
    sat_freqs = saturation_values.keys()
    closest_index = np.abs(np.subtract(sat_freqs, freq)).argmin()

    closest_freq = sat_freqs[closest_index]
    next_freq = sat_freqs[min(closest_index + 1, len(sat_freqs) - 1)]
    freq_diff = (next_freq - closest_freq)
    if freq_diff == 0:
        saturation = saturation_values[closest_freq]
    else:
        variance = abs(freq - closest_freq) / freq_diff
        closest_sat = saturation_values[closest_freq]
        saturation = closest_sat + abs(closest_sat - saturation_values[next_freq]) * variance
    saturation += attenuation

    return saturation

def capture_sweep_spectrum(dut, mode, points, dec = 1, fshift = 0, packets = 1):

    usable_bins = compute_usable_bins(dut.properties, mode, points, dec, fshift)

    total_pow = []
    samples = int(points / packets)
    # read data
    for p in range(packets):
        if p == 0:
            data, context = collect_data_and_context(dut)

        else:
            d, c = collect_data_and_context(dut, samples)
            data.data.np_array = np.concatenate([data.data.np_array, d.data.np_array])
    
    # adjust fstart and fstop based on the spectral inversion
    usable_bins, fstart, fstop = adjust_usable_fstart_fstop(
        dut.properties,
        mode,
        points,
        dec,
        context['rffreq'],
        data.spec_inv,
        usable_bins)
    # compute fft
    pow_data = compute_fft(dut, data, context)
    if not len(total_pow):
        total_pow = pow_data
    else:
        total_pow = np.add(total_pow, pow_data)
    pow_data = total_pow
    # trim FFT
    pow_data, usable_bins, fstart, fstop = trim_to_usable_fstart_fstop(pow_data, 
                                                                    usable_bins,  
                                                                    fstart,  
                                                                    fstop)

    return (fstart, fstop, pow_data, context)