import math

from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)

def compute_fft(dut, data_pkt, context):
    """
    Return an array of dBm values by computing the FFT of
    the passed data and reference level.

    :param dut: WSA device
    :type dut: pyrf.devices.thinkrf.WSA
    :param data_pkt: packet containing samples
    :type data_pkt: pyrf.vrt.DataPacket
    :param context: dict containing context values

    This function uses only *dut.ADC_DYNAMIC_RANGE*,
    *data_pkt.data* and *context['reflevel']*.

    :returns: numpy array of dBm values as floats
    """
    import numpy # import here so docstrings are visible even without numpy

    reference_level = context['reflevel']
    prop = dut.properties

    data = data_pkt.data.numpy_array()
    if data_pkt.stream_id == VRT_IFDATA_I14Q14:
        i_data = numpy.array(data[:,0], dtype=float)
        q_data = numpy.array(data[:,1], dtype=float)

        # special handling of WSA4k "only I data is valid here" range
        freq = context['rffreq']
        for low, high, valid_data in prop.CAPTURE_FREQ_RANGES:
            if low <= freq <= high:
                break

        if valid_data == I_ONLY:
            power_spectrum = _compute_fft_i_only(i_data)
        power_spectrum = _compute_fft(i_data, q_data)

    if data_pkt.stream_id in (VRT_IFDATA_I14, VRT_IFDATA_I24):
        i_data = numpy.array(data, dtype=float)
        power_spectrum = _compute_fft_i_only(i_data)

    if data_pkt.stream_id == VRT_IFDATA_PSD8:
        power_spectrum = numpy.array(data, dypye=float)

    noiselevel_offset = (
        reference_level - prop.NOISEFLOOR_CALIBRATION - prop.ADC_DYNAMIC_RANGE)
    return power_spectrum + noiselevel_offset


def _compute_fft(i_data, q_data):
    import numpy

    i_removed_dc_offset = i_data - numpy.mean(i_data)
    q_removed_dc_offset = q_data - numpy.mean(q_data)
    calibrated_q = _calibrate_i_q(i_removed_dc_offset, q_removed_dc_offset)
    iq = i_removed_dc_offset + 1j * calibrated_q
    windowed_iq = iq * numpy.hanning(len(i_data))

    power_spectrum = numpy.fft.fftshift(numpy.fft.fft(windowed_iq))
    power_spectrum = 20 * numpy.log10(numpy.abs(power_spectrum)/len(power_spectrum))

    median_index = len(power_spectrum) // 2
    power_spectrum[median_index] = (power_spectrum[median_index - 1]
        + power_spectrum[median_index + 1]) / 2
    return power_spectrum

def _compute_fft_i_only(i_data):
    import numpy

    windowed_i = i_data * numpy.hanning(len(i_data))

    power_spectrum = numpy.fft.rfft(windowed_i)
    power_spectrum = 20 * numpy.log10(numpy.abs(power_spectrum)/len(power_spectrum))
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


