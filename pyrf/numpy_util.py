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

    linear = np.power(10, np.divide(power_spectrum,20))

    channel_power = 10 * np.log10(np.sum(np.square(linear)))
    return channel_power

def _decode_data_pkts(data_pkt):
    stream_id = data_pkt.stream_id
    spec_inv = data_pkt.spec_inv
    i_data = None
    q_data = None

    if stream_id == VRT_IFDATA_I14Q14:
        i_data = np.array(data_pkt.data.numpy_array()[:,0], dtype=float) / 2 ** 13
        q_data = np.array(data_pkt.data.numpy_array()[:,1], dtype=float) / 2 ** 13

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

def compute_fft(dut, data_pkt, context, correct_phase=True,
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

    if 'reflevel' in context:
        reference_level = context['reflevel']
    else:
        reference_level = ref
    prop = dut.properties

    if stream_id == VRT_IFDATA_I14Q14:

        decimation = dut.decimation()
        if 'iqswap' in context:
            iq_swap = context['iqswap']
        else:
            iq_swap = 0
        power_spectrum = _compute_fft(i_data, q_data, correct_phase, iq_swap, context['bandwidth'], decimation,
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

def _compute_fft(i_data, q_data, correct_phase, iqswapedbit, Rx_Bw,
        hide_differential_dc_offset, convert_to_dbm, apply_window, decimation):

    Nsamp = len(i_data)
    rbw = Rx_Bw/Nsamp

    if hide_differential_dc_offset:
        i_data = i_data - np.mean(i_data)
        q_data = q_data - np.mean(q_data)
    
    if apply_window:
        i_data = i_data * np.hanning(len(i_data))
        q_data = q_data * np.hanning(len(q_data))
    
    if correct_phase:
        phi2_deg = 52
        # Measuring phase error
        phi1, Phi1_deg = measurePhaseError(i_data, q_data)
        if decimation <= 32: # F.D
            if abs(Phi1_deg) < phi2_deg:
                # T.D correction
                i_cal, q_cal = _calibrate_i_q_tarek1(i_data, q_data, phi1)
                # F.D correction
                i_data, q_data = imageAttenuation(i_cal, q_cal, rbw, Rx_Bw, iqswapedbit, phi1, decimation)
            else:
                # F.D correction only at the edges
                q_data = q_data * np.sqrt(sum(i_data ** 2)/sum(q_data ** 2))  
                i_data, q_data = imageAttenuation(i_data, q_data, rbw, Rx_Bw, iqswapedbit, phi1, decimation)
        else:
            # T.D correction only at the decimation level > 32
            i_data, q_data = _calibrate_i_q_tarek1(i_data, q_data, phi1)
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

def _calibrate_i_q_tarek1(i_data, q_data, phi1):
    print 'got here'
    Nsamp = len(i_data)
    # Correcting for gain imbalance
    q_data = q_data * np.sqrt(np.var(i_data)/np.var(q_data))  
    # Correcting for phase error
    cFactor = (1 / np.cos(phi1)) - 1
    q_cal = (q_data - i_data * np.sin(phi1)) * cFactor
    # Recorrecting for gain imbalance
    q_cal = q_cal * np.sqrt(np.var(i_data)/np.var(q_cal))
    return i_data, q_cal

def measurePhaseError(i_data, q_data):
    IQprod = np.inner(i_data,q_data)
    phi1 = pi/2 - np.arccos(IQprod / (np.sqrt(np.sum(np.square(i_data)) * np.sum(np.square(q_data)))))
    Phi1_deg = phi1 * 180/pi
    return phi1, Phi1_deg

def imageAttenuation(i_in, q_in, rbw, Rx_Bw, iqswapedbit, phi1, decimation):
    
    Nsamp = len(i_in)
    BWmax_ndx = int(np.rint(20e6/rbw))					# max BW indices to attenuate
    chSpacing = int(np.rint(200e3/rbw))					# max BW indices to attenuate
    BWmin_ndx = int(np.rint(300e3/rbw/decimation))		# min BW indices to attenuate
    BW_ht_ndx = int(np.rint(100e3/rbw))					# head and tail indices of BW to attenuate
    Nstep = max(1, np.rint(300e3/rbw))
    ImgToNoise_thresh = 5;  			                # Image-to-Noise threshold (10)
    if abs(phi1*180/pi) > 30.0:				            # Image-to-Signal threshold
        ImgToSig_thresh = 0.005;
    else:
        ImgToSig_thresh = 0.05
    
    iq = i_in + 1j * q_in
    iq = iq * np.hanning(len(i_in))
    ampl_spectrum = np.fft.fftshift(np.fft.fft(iq))/Nsamp

    ampl_spectrum_mag = np.abs(ampl_spectrum)
    from scipy.interpolate import UnivariateSpline
    p, x = np.histogram(ampl_spectrum_mag, bins=int(len(ampl_spectrum_mag)/Nstep))
    x = x[:-1] + (x[1] - x[0])/2 
    f = UnivariateSpline(x, p, s=int(len(ampl_spectrum_mag)/Nstep))
    N_ndx = max(enumerate(p),key=lambda x: x[1])[0]
    N = x[N_ndx]
    
    if np.max(ampl_spectrum_mag) > 20 * N:						# To ensure signal presence
        maxNdx = np.argmax(ampl_spectrum_mag)
        ind = [i for i,v in enumerate(ampl_spectrum_mag) if v > ImgToNoise_thresh * N and v > ImgToSig_thresh * np.max(ampl_spectrum_mag) and maxNdx-BWmax_ndx < i < maxNdx+BWmax_ndx]
        
        # Removing values beyond channel spacing
        for i in range(np.argmax(ampl_spectrum_mag[ind]), 0, -1):
            if abs(ind[i] - ind[i-1]) < chSpacing:  j1 = i
            else:   break
        for i in range(np.argmax(ampl_spectrum_mag[ind]), len(ind)-1):
            if abs(ind[i] - ind[i+1]) < chSpacing:  j2 = i
            else:   break
        ind = ind[j1-1:j2]
        
        if ind != []:
            head = min(ind) - max(3, BW_ht_ndx)
            tail = max(ind) + max(3, BW_ht_ndx)
            ind = filter(lambda x: 0 <= x <= Nsamp, range(head, tail+1))
            midNdx = ind[len(ind)/2]
            ind_mirror = np.subtract(Nsamp-1,ind)
            
            if Nsamp/2 in ind:
                if Nsamp/2 in range(midNdx - max(5, BWmin_ndx), midNdx + max(5, BWmin_ndx)):
                    ind = []
                else:
                    if midNdx > Nsamp/2:
                        ind = [v for i,v in enumerate(ind) if v > midNdx]
                    if midNdx <= Nsamp/2:
                        ind = [v for i,v in enumerate(ind) if v < midNdx]
                    ind_mirror = np.subtract(Nsamp-1,ind)
            if ind != []:
                allIndices = np.concatenate([ind,ind_mirror])
                if iqswapedbit == 0:
                    if phi1 > 0:
                        att_ind = filter(lambda x: x < Nsamp/2, allIndices)
                    else:
                        att_ind = filter(lambda x: x > Nsamp/2, allIndices)
                if iqswapedbit == 1:
                    if phi1 < 0:
                        att_ind = filter(lambda x: x < Nsamp/2, allIndices)
                    else:
                        att_ind = filter(lambda x: x > Nsamp/2, allIndices)
                
                
                Natt = np.random.normal(0, 15*float(float(len(att_ind))/Nsamp/decimation)*N, len(att_ind)) + 1j * np.random.normal(0, 15*float(float(len(att_ind))/Nsamp/decimation)*N, len(att_ind))
                
                ampl_spectrum[att_ind] = (ampl_spectrum[att_ind]/np.abs(ampl_spectrum[att_ind])) * Natt
                iq = np.fft.ifft(np.fft.fftshift(ampl_spectrum*Nsamp))
                i_data = np.real(iq); q_data = np.imag(iq)
            else:
                i_data = i_in; q_data = q_in
        else:
            i_data = i_in; q_data = q_in
    else:
        i_data = i_in; q_data = q_in
    i_data = i_data - np.mean(i_data)
    q_data = q_data - np.mean(q_data)
          
    return i_data, q_data
