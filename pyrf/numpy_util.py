import math
import numpy as np
from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)

def calculate_channel_power(power_spectrum):
    """
    Return a dBm value representing the channel power of the input
    power spectrum.
    :param power_spectrum: array containing power spectrum to be used for
                            the channel power calculation
    """
    linear = np.power(10, power_spectrum / 20)

    channel_power = 10 * np.log10(np.sum(np.square(linear)))
    return channel_power

def compute_fft(dut, data_pkt, context, correct_phase=True,
        hide_differential_dc_offset=True, convert_to_dbm=True, 
        apply_window=True, apply_spec_inv=True, apply_reference=True,ref=None):
    """
    Return an array of dBm values by computing the FFT of
    the passed data and reference level.

    :param dut: WSA device
    :type dut: pyrf.devices.thinkrf.WSA
    :param data_pkt: packet containing samples
    :type data_pkt: pyrf.vrt.DataPacket
    :param context: dict containing context values
    :param correct_phase: apply phase correction for captures with IQ data
    :param hide_differential_dc_offset: mask the differential DC offset
                                        present in captures with IQ data
    :param convert_to_dbm: convert the output values to dBm

    :returns: numpy array of dBm values as floats
    """
    import numpy as np # import here so docstrings are visible even without numpy
    import numpy # import here so docstrings are visible even without numpy

    if not type(data_pkt) is list:
        data_pkt = [data_pkt]

    i_data, q_data, stream_id, spec_inv = _decode_data_pkts(data_pkt)
    if 'reflevel' in context:
        reference_level = context['reflevel']
    else:
        reference_level = ref
    prop = dut.properties

    if stream_id == VRT_IFDATA_I14Q14:

        # special handling of WSA4k "only I data is valid here" range
        if 'rffreq' in context:
            freq = context['rffreq']
            for low, high, valid_data in prop.CAPTURE_FREQ_RANGES:
                if low <= freq <= high:
                    break

            if valid_data == I_ONLY:
                power_spectrum = _compute_fft_i_only(i_data, convert_to_dbm, apply_window)
        power_spectrum = _compute_fft(i_data, q_data, correct_phase,
            hide_differential_dc_offset, convert_to_dbm, apply_window)

    if stream_id == VRT_IFDATA_I14:
        power_spectrum = _compute_fft_i_only(i_data, convert_to_dbm, apply_window)

    if stream_id == VRT_IFDATA_I24:
        power_spectrum = _compute_fft_i_only(i_data, convert_to_dbm, apply_window)

    if stream_id == VRT_IFDATA_PSD8:
        # TODO: handle convert_to_dbm option
        power_spectrum = np.array(data, dtype=float)

    if apply_spec_inv:
        if spec_inv:  # handle inverted spectrum
            power_spectrum = np.flipud(power_spectrum)
    if apply_reference:
        noiselevel_offset = reference_level + prop.REFLEVEL_ERROR
        return power_spectrum + noiselevel_offset
    return power_spectrum

def _decode_data_pkts(data_pkt):
    stream_id = data_pkt[0].stream_id
    spec_inv = data_pkt[0].spec_inv
    i_data = None
    q_data = None

    if stream_id == VRT_IFDATA_I14Q14:
        for d in data_pkt:
            if i_data is None:
                i_data = np.array(d.data.numpy_array()[:,0], dtype=float) / 2 ** 13
                q_data = np.array(d.data.numpy_array()[:,1], dtype=float) / 2 ** 13
            else:
                i_data = np.append(i_data, np.array(d.data.numpy_array()[:,0], dtype=float) / 2 ** 13)
                q_data = np.append(q_data, np.array(d.data.numpy_array()[:,1], dtype=float) / 2 ** 13)
    
    if stream_id == VRT_IFDATA_I14:
        for d in data_pkt:
            if i_data is None:
                i_data = np.array(d.data.numpy_array(), dtype=float) / 2 ** 13
            else:
                i_data = np.append(i_data, np.array(d.data.numpy_array(), dtype=float) / 2 ** 13)

    if stream_id == VRT_IFDATA_I24:
        for d in data_pkt:
            if i_data is None:
                i_data = np.array(d.data.numpy_array(), dtype=float) / 2 ** 23
            else:
                i_data = np.append(i_data, np.array(d.data.numpy_array(), dtype=float) / 2 ** 23)

    return i_data, q_data, stream_id, spec_inv

def _compute_fft(i_data, q_data, correct_phase,
        hide_differential_dc_offset, convert_to_dbm, apply_window):
    import numpy as np

    if hide_differential_dc_offset:
        i_data = i_data - np.mean(i_data)
        q_data = q_data - np.mean(q_data)
    if correct_phase:
        calibrated_q = _calibrate_i_q(i_data, q_data)
    else:
        calibrated_q = q_data
    iq = i_data + 1j * calibrated_q

    if apply_window:
        iq = iq * np.hanning(len(i_data))

    power_spectrum = np.abs(np.fft.fftshift(np.fft.fft(iq)))/len(i_data)
    if convert_to_dbm:
        power_spectrum = 20 * np.log10(power_spectrum)

    if hide_differential_dc_offset:
        median_index = len(power_spectrum) // 2
        power_spectrum[median_index] = (power_spectrum[median_index - 1]
            + power_spectrum[median_index + 1]) / 2
    return power_spectrum

def _compute_fft_i_only(i_data, convert_to_dbm, apply_window):
    import numpy as np
    if apply_window:
        i_data = i_data * np.hanning(len(i_data))

    power_spectrum = np.abs(np.fft.rfft(i_data))/len(i_data)
    if convert_to_dbm:
        power_spectrum = 20 * np.log10(power_spectrum)
    return power_spectrum

def _calibrate_i_q(i_data, q_data):
    samples = len(i_data)

    sum_of_squares_i = sum(i_data ** 2)
    sum_of_squares_q = sum(q_data ** 2)

    amplitude = math.sqrt(sum_of_squares_i * 2 / samples)
    ratio = math.sqrt(sum_of_squares_i / sum_of_squares_q)

    p = (q_data / amplitude) * ratio * (i_data / amplitude)

    sinphi = 2 * sum(p) / samples
    phi_est = -math.asin(sinphi)

    return (math.sin(phi_est) * i_data + ratio * q_data) / math.cos(phi_est)


