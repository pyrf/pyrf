from pyrf.numpy_util import compute_fft
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
    def __init__(self, real_device, async_callback=None):
        
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


    def capture_power_spectrum(self, device_set, rbw, min_points=128):
        """
        Initiate a capture of power spectral density by
        applying leveled triggers and return the first data packet that
        satisfy the trigger.

        :param fstart: starting frequency in Hz
        :type fstart: float
        :param fstop: ending frequency in Hz
        :type fstop: float
        :param rbw: requested RBW in Hz (output RBW may be smaller than
                    requested)
        :type rbw: float
        :param triggers: a class containing trigger information
        :type class:`TriggerSettings`
        :param device_settings: antenna, gain and other device settings
        :type dict:
        """

        prop = self.real_device.properties

        # setup the WSA device
        self.fstart = device_set['freq'] - prop.USABLE_BW / 2
        self.fstop =  device_set['freq'] + prop.USABLE_BW / 2
        self.real_device.apply_device_settings(device_set)
        
        self.real_device.abort()
        self.real_device.flush()
        self.real_device.request_read_perm()
        self._vrt_context = {}

        points = prop.FULL_BW / rbw
        points = max(min_points, 2 ** math.ceil(math.log(points, 2)))

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

        pow_data = compute_fft(self.real_device, packet, self._vrt_context)
        prop = self.real_device.properties
        attenuated_edge = math.ceil((1.0 -
            float(prop.USABLE_BW) / prop.FULL_BW) / 2 * len(pow_data))
        pow_data = pow_data[attenuated_edge:-attenuated_edge]
        # FIXME: fstart and fstop not properly corrected for bins removed

        if self.async_callback:
            self.async_callback(self.fstart, self.fstop, pow_data)
            return
        return (self.fstart, self.fstop, pow_data)
