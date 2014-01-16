from pyrf.config import TriggerSettings

import math


class CaptureDeviceError(Exception):
    pass


class CaptureDevice(object):
    """
    Virtual device that returns power levels generated from a single data packet
    :param real_device: device that will will be used for capturing data,
                        typically a :class:`pyrf.thinkrf.WSA` instance.
    :param callback: callback to use for async operation (not used if
                     real_device is using a :class:`PlainSocketConnector`)

    """    
    def __init__(self, real_device, device_set = None, async_callback=None):
        
        self.real_device = real_device
        self.connector = self.real_device.connector
        if hasattr(self.connector, 'vrt_callback'):
            if not async_callback:
                raise CaptureDeviceError(
                    "async_callback required for async operation")
            # disable receiving data until we are expecting it
            self.connector.vrt_callback = None
        else:
            if async_callback:
                raise CaptureDeviceError(
                    "async_callback not applicable for sync operation")
        self.async_callback = async_callback
        
        if device_set is not None:
            self.configure_device(device_set)
    
    def configure_device(self, device_set):
        """
        Configure the device settings
        :param device_settings: attenuator, decimation frequency shift 
                                and other device settings
        :type dict:
        """
        self.real_device.apply_device_settings(device_set)
        self._device_set = device_set
        
    def capture_time_domain(self, rbw, device_set = None, min_points=128):
        """
        Initiate a capture of raw time domain IQ or I-only data

        :param rbw: requested RBW in Hz (output RBW may be smaller than
                    requested)
        :type rbw: float
        :param device_settings: attenuator, decimation frequency shift 
                                and other device settings
        :type dict:
        :param min_points: smallest number of points per capture from real_device
        :type min_points: int
        """
        prop = self.real_device.properties
        
        if device_set is not None:
            self.configure_device(device_set)
        rfe_mode = self._device_set['rfe_mode']
        full_bw = prop.FULL_BW[rfe_mode]
        usable_bw = prop.USABLE_BW[rfe_mode]
        pass_band_center = prop.PASS_BAND_CENTER[rfe_mode]
        
        freq = self._device_set['freq']
        self.fstart = freq - full_bw * pass_band_center
        self.fstop = freq + full_bw * (1 - pass_band_center)

        self.real_device.abort()
        self.real_device.flush()
        self.real_device.request_read_perm()
        self._vrt_context = {}

        points = round(max(min_points, full_bw / rbw))
        points = 2 ** math.ceil(math.log(points, 2))

        if rfe_mode == 'ZIF':
            self.usable_bins = [(
                int((pass_band_center - float(usable_bw) / full_bw / 2) * points),
                int(points * float(usable_bw) / full_bw))]
        else:
            self.usable_bins = [(
                int((pass_band_center - float(usable_bw) / full_bw / 2) * points / 2),
                int(points / 2 * float(usable_bw) / full_bw))]

        if self.async_callback:
            self.connector.vrt_callback = self.read_data
            self.real_device.capture(points, 1)

            return

        self.real_device.capture(points, 1)
        result = None
        while result is None:
            result = self.read_data(self.real_device.read())
        return result

    def read_data(self, packet):
        if packet.is_context_packet():
            self._vrt_context.update(packet.fields)
            return
        data= {
            'context_pkt' : self._vrt_context,
            'data_pkt' : packet}

        # FIXME: fstart and fstop not properly corrected for bins removed

        if self.async_callback:
            self.async_callback(self.fstart, self.fstop, data)
            return
        return (self.fstart, self.fstop, data)
