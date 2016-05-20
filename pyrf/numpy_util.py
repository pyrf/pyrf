import numpy as np
import random
pi = np.pi



from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)


def calculate_channel_power(power_spectrum):
    """
    Return a dBm value representing the channel power of the input
    power spectrum.
    :param power_spectrum: array containing power spectrum to be used for
                            the channel power calculation
    """

    linear = np.power(10, np.divide(power_spectrum, 20))

    channel_power = 10 * np.log10(np.sum(np.square(linear)))
    return channel_power


def _decode_data_pkts(data_pkt):
    stream_id = data_pkt.stream_id
    spec_inv = data_pkt.spec_inv
    i_data = None
    q_data = None

    if stream_id == VRT_IFDATA_I14Q14:
        i_data = np.array(data_pkt.data.numpy_array()[:, 0], dtype=float) / 2 ** 13
        q_data = np.array(data_pkt.data.numpy_array()[:, 1], dtype=float) / 2 ** 13

    if stream_id == VRT_IFDATA_I14:
        i_data = (np.array(data_pkt.data.numpy_array(), dtype=float) / 2 ** 13)

    if stream_id == VRT_IFDATA_I24:
        i_data = np.array(data_pkt.data.numpy_array(), dtype=float) / 2 ** 23

    return i_data, q_data, stream_id, spec_inv


def _compute_fft_i_only(i_data, convert_to_dbm, apply_window):
    if apply_window:
        i_data = i_data * np.hanning(len(i_data))

    power_spectrum = np.abs(np.fft.rfft(i_data))/len(i_data)
    if convert_to_dbm:
        power_spectrum = 20 * np.log10(power_spectrum)
    return power_spectrum


def compute_fft(dut, data_pkt, context, correct_phase=True, iq_correction_wideband = True,
        hide_differential_dc_offset=True, convert_to_dbm=True, 
        apply_window=True, apply_spec_inv=True, apply_reference=True,ref=None, decimation=1):
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

    i_data, q_data, stream_id, spec_inv = _decode_data_pkts(data_pkt)
    if not 'bandwidth' in context:
        context['bandwidth'] = 1e9
    if 'reflevel' in context:
        reference_level = context['reflevel']
    else:
        reference_level = ref
    prop = dut.properties

    if stream_id == VRT_IFDATA_I14Q14:

        if 'iqswap' in context:
            iq_swap = context['iqswap']
        else:
            iq_swap = 0
        power_spectrum = _compute_fft(i_data, q_data, correct_phase, iq_correction_wideband,
            hide_differential_dc_offset, convert_to_dbm, apply_window, decimation, iq_swap, context['bandwidth'])

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


def _compute_fft(i_data, q_data, correct_phase, iq_correction_wideband,
        hide_differential_dc_offset, convert_to_dbm, apply_window, decimation, iqswapedbit, Rx_Bw):

    Nsamp = len(i_data)
    rbw = Rx_Bw/Nsamp

    if hide_differential_dc_offset:
        i_data = i_data - np.mean(i_data)
        q_data = q_data - np.mean(q_data)

    if apply_window:
        i_data = i_data * np.hanning(len(i_data))
        q_data = q_data * np.hanning(len(q_data))

    if correct_phase:
        phi2_deg = 52   # phase error after which the T.D algorithm is skipped to avoid noise floor jumping
        # Measuring phase error
        phi_rad, Phi_deg = measure_phase_error(i_data, q_data)
        if decimation == 1:  # F.D + T.D corrections
            if abs(Phi_deg) < phi2_deg:
                # T.D correction
                i_cal, q_cal = _calibrate_i_q(i_data, q_data, phi_rad)
                # F.D correction
                i_data, q_data = image_attenuation(i_cal, q_cal, Phi_deg, iqswapedbit, iq_correction_wideband, Rx_Bw, rbw)
            else:
                # F.D correction only at the edges
                q_data = q_data * np.sqrt(sum(i_data ** 2)/sum(q_data ** 2))
                i_data, q_data = image_attenuation(i_data, q_data, Phi_deg, iqswapedbit, iq_correction_wideband, Rx_Bw, rbw)
        else:
            # Only T.D correction at the decimation level > 1
            i_data, q_data = _calibrate_i_q(i_data, q_data, phi_rad)
        i_data = i_data - np.mean(i_data)
        q_data = q_data - np.mean(q_data)

    iq = i_data + 1j * q_data

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


def _calibrate_i_q(i_data, q_data, phi_rad):

    Nsamp = len(i_data)
    # Correcting for gain imbalance
    q_data = q_data * np.sqrt(np.var(i_data)/np.var(q_data))
    # Correcting for phase error
    cFactor = (1 / np.cos(phi_rad)) - 1
    q_cal = (q_data - i_data * np.sin(phi_rad)) * cFactor
    # Recorrecting for gain imbalance
    q_cal = q_cal * np.sqrt(np.var(i_data)/np.var(q_cal))
    return i_data, q_cal


def measure_phase_error(i_data, q_data):
    IQprod = np.inner(i_data, q_data)
    phi_rad = pi/2 - np.arccos(IQprod / (np.sqrt(np.sum(np.square(i_data)) * np.sum(np.square(q_data)))))
    Phi_deg = phi_rad * 180/pi
    return phi_rad, Phi_deg


def image_attenuation(i_in, q_in, Phi_deg, iqswapedbit, iq_correction_wideband, Rx_Bw, rbw):

    Nsamp = len(i_in)
    BWmax_ndx = int(np.rint(20e6/rbw))          # max BW indices to attenuate
    if iq_correction_wideband:
        chSpacing = int(np.rint(1000e3/rbw))    # max channel spacing in case of NB signals
    else:
        chSpacing = int(np.rint(200e3/rbw))     # max channel spacing in case of WB signals
    BWmin_ndx = int(np.rint(300e3/rbw))         # min BW indices to attenuate
    BW_ht_ndx = int(np.rint(100e3/rbw))         # head and tail indices of BW to attenuate
    Nstep = max(1, np.rint(300e3/rbw))

    iq = i_in + 1j * q_in
    iq = iq * np.hanning(len(i_in))
    ampl_spectrum = np.fft.fftshift(np.fft.fft(iq))/Nsamp

    ampl_spectrum_mag = np.abs(ampl_spectrum)

    p, x = np.histogram(ampl_spectrum_mag, bins=int(len(ampl_spectrum_mag)/Nstep))
    x = x[:-1] + (x[1] - x[0])/2
    N_ndx = max(enumerate(p), key=lambda x: x[1])[0]
    N = x[N_ndx]

    ToNoise_thresh = 5 * N                      # Relative-to-Noise threshold
    if abs(Phi_deg) > 30.0:                     # Relative-to-Signal threshold
        ToMax_thresh = 0.005 * np.max(ampl_spectrum_mag)
    else:
        ToMax_thresh = 0.05 * np.max(ampl_spectrum_mag)

    if np.max(ampl_spectrum_mag) > 10 * N:  # To ensure signal presence (3.16=>10dB, 5.6=>15dB, 10=>20dB, 20=>26dB)
        maxNdx = np.argmax(ampl_spectrum_mag)
        ind = [i for i, v in enumerate(ampl_spectrum_mag) if v > ToNoise_thresh and v > ToMax_thresh and maxNdx-BWmax_ndx < i < maxNdx+BWmax_ndx]

        #Removing values beyond channel spacing
        j1 = 0
        j2 = len(ind)-1
        for i in range(np.argmax(ampl_spectrum_mag[ind]), 0, -1):
            if abs(ind[i] - ind[i-1]) < chSpacing:
                j1 = i
            else:
                break
        for i in range(np.argmax(ampl_spectrum_mag[ind]), len(ind)-1):
            if abs(ind[i] - ind[i+1]) < chSpacing:
                j2 = i
            else:
                break
        ind = ind[j1-1:j2]

        if ind != []:
            head = min(ind) - max(3, BW_ht_ndx)
            tail = max(ind) + max(3, BW_ht_ndx)
            ind = filter(lambda x: 0 <= x <= Nsamp, range(head, tail+1))
            midNdx = ind[len(ind)/2]

            if Nsamp/2 in ind:
                if Nsamp/2 in range(midNdx - max(5, BWmin_ndx), midNdx + max(5, BWmin_ndx)):
                    ind = []
                    att_ind = []
                else:
                    if midNdx > Nsamp/2:
                        ind_mirror = range(Nsamp-1-max(ind), min(ind))
                    else:
                        ind_mirror = range(min(Nsamp-1, max(ind)), Nsamp-1-min(ind))
                    # ind_mirror = filter(lambda x: x not in ind, ind_mirror)   # Too slow
            else:
                ind_mirror = np.subtract(Nsamp-1, ind)
            if ind != []:
                allIndices = np.concatenate([ind, ind_mirror])
                if abs(Phi_deg) > 10:   # added as the zero degree doesn't fall exactly on the center frequency
                    if iqswapedbit == 0:
                        if Phi_deg > 0:
                            att_ind = filter(lambda x: x < Nsamp/2, allIndices)
                        else:
                            att_ind = filter(lambda x: x > Nsamp/2, allIndices)
                    if iqswapedbit == 1:
                        if Phi_deg < 0:
                            att_ind = filter(lambda x: x < Nsamp/2, allIndices)
                        else:
                            att_ind = filter(lambda x: x > Nsamp/2, allIndices)
                else:
                    att_ind = ind_mirror

                if att_ind != []:
                    if np.max(att_ind) > Nsamp-1 or np.min(att_ind) <  0:   # the if statement can be removed if it'll be faster
                        att_ind = range(max(0, min(att_ind)), min(max(att_ind), Nsamp))

                    tmparray = np.delete(ampl_spectrum_mag, allIndices)
                    p, x = np.histogram(tmparray, bins=int(len(tmparray)/Nstep))
                    N_ndx = max(enumerate(p), key=lambda x: x[1])[0]
                    N = np.sqrt(2) * x[N_ndx]

                    Natt = np.random.normal(0, N, len(att_ind)) + 1j * np.random.normal(0, N, len(att_ind))
                    ampl_spectrum[att_ind] = (ampl_spectrum[att_ind]/np.abs(ampl_spectrum[att_ind])) * Natt
                    iq = np.fft.ifft(np.fft.fftshift(ampl_spectrum*Nsamp))
                    i_data = np.real(iq)
                    q_data = np.imag(iq)
                else:
                    i_data = i_in
                    q_data = q_in
            else:
                i_data = i_in
                q_data = q_in
        else:
            i_data = i_in
            q_data = q_in
    else:
        i_data = i_in
        q_data = q_in
    i_data = i_data - np.mean(i_data)
    q_data = q_data - np.mean(q_data)

    return i_data, q_data
