import math

from pyrf.vrt import I_ONLY

FFT_BASELINE = -10

def compute_fft(dut, data_pkt, context):
    """
    Return an array of dBm values by computing the FFT of
    the passed data and reference level.

    :param dut: WSA device
    :type dut: pyrf.devices.thinkrf.WSA4000
    :param data_pkt: packet containing samples
    :type data_pkt: pyrf.vrt.DataPacket
    :param context: dict containing context values

    This function uses only *dut.ADC_DYNAMIC_RANGE*,
    *data_pkt.data* and *context['reflevel']*.

    :returns: numpy array of dBm values as floats
    """
    import numpy # import here so docstrings are visible even without numpy

    reference_level = context['reflevel']

    iq_data = data_pkt.data.numpy_array()
    # i, q values here are 14-bit signed
    i_data = numpy.array(iq_data[:,0], dtype=float) / 2**13
    q_data = numpy.array(iq_data[:,1], dtype=float) / 2**13

    freq = context['rffreq']
    for low, high, valid_data in dut.CAPTURE_FREQ_RANGES:
        if low <= freq <= high:
            break
    if valid_data == I_ONLY:
        return _compute_fft_i_only(i_data, reference_level, dut.ADC_DYNAMIC_RANGE)
    return _compute_fft(i_data, q_data, reference_level, dut.ADC_DYNAMIC_RANGE)

def _compute_fft(i_data, q_data, reference_level, adc_dynamic_range):
    import numpy

    i_removed_dc_offset = i_data - numpy.mean(i_data)
    q_removed_dc_offset = q_data- numpy.mean(q_data)
    calibrated_q = _calibrate_i_q(i_removed_dc_offset, q_removed_dc_offset)
    iq = i_removed_dc_offset + 1j * calibrated_q
    windowed_iq = iq * numpy.hanning(len(i_data))

    noise_level_offset = reference_level - FFT_BASELINE - adc_dynamic_range

    fft_result = numpy.fft.fftshift(numpy.fft.fft(windowed_iq))
    fft_result = 20 * numpy.log10(numpy.abs(fft_result)) + noise_level_offset

    median_index = len(fft_result) // 2
    fft_result[median_index] = (fft_result[median_index - 1]
        + fft_result[median_index + 1]) / 2
    return fft_result

def _compute_fft_i_only(i_data, reference_level, adc_dynamic_range):
    import numpy

    windowed_i = i_data * numpy.hanning(len(i_data))

    noise_level_offset = reference_level - FFT_BASELINE - adc_dynamic_range

    fft_result = numpy.fft.fftshift(numpy.fft.fft(windowed_i))
    fft_result = 20 * numpy.log10(numpy.abs(fft_result)) + noise_level_offset

    median_index = len(fft_result) // 2
    return fft_result[median_index+1:]

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


