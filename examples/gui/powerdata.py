import numpy
import math

def read_power_data(dut, reference_level=None):
    # capture 1 packet
    dut.capture(1024, 1)

    # read until I get 1 data packet
    while not dut.eof():
        pkt = dut.read()

        if pkt.is_data_packet():
            break

        if 'reflevel' in pkt.fields:
            reference_level = pkt.fields['reflevel']

    assert reference_level is not None, pkt

    iq_data = pkt.data.numpy_array()
    i_data = numpy.array(iq_data[:,0], dtype=float) / len(iq_data)
    q_data = numpy.array(iq_data[:,1], dtype=float) / len(iq_data)
    return calculate_fft(i_data, q_data, reference_level), reference_level


def calculate_fft(i_data, q_data, reference_level):
    calibrated_q = calibrate_i_q(i_data, q_data)
    i_removed_dc_offset = i_data - numpy.mean(i_data)
    q_removed_dc_offset = calibrated_q - numpy.mean(calibrated_q)
    iq = i_removed_dc_offset + 1j * q_removed_dc_offset
    windowed_iq = iq * numpy.hanning(len(i_data))

    FFT_BASELINE = -28.5
    ADC_DYNAMIC_RANGE = 72.5
    noise_level_offset = reference_level - FFT_BASELINE - ADC_DYNAMIC_RANGE

    fft_result = numpy.fft.fftshift(numpy.fft.fft(windowed_iq))
    fft_result = 20 * numpy.log10(numpy.abs(fft_result)) + noise_level_offset

    median_index = len(fft_result) // 2
    fft_result[median_index] = (fft_result[median_index - 1]
        + fft_result[median_index + 1]) / 2
    return fft_result


def calibrate_i_q(i_data, q_data):
    samples = len(i_data)

    sum_of_squares_i = sum(i_data ** 2)
    sum_of_squares_q = sum(q_data ** 2)

    amplitude = math.sqrt(sum_of_squares_i * 2 / samples)
    ratio = math.sqrt(sum_of_squares_i / sum_of_squares_q)

    p = (q_data / amplitude) * ratio * (i_data / amplitude)

    sinphi = 2 * sum(p) / samples
    phi_est = -math.asin(sinphi)

    return (math.sin(phi_est) * i_data + ratio * q_data) / math.cos(phi_est)


