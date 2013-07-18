from pyrf.numpy_util import compute_fft
from pyrf.config import TriggerSettings

USABLE_BW = 100e6

class CaptureDeviceError(Exception):
    pass


class CaptureDevice(object):
    """
    Virtual device that returns power levels generated from a single data packet
    (packet returned will have a span of 100MHz)
    :param real_device: device that will will be used for capturing data,
                        typically a :class:`WSA4000` instance.
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

    
    
    
    def capture_power_spectrum(self,device_set, bins):
        """
        Initiate a capture of power spectral density by
        applying leveled triggers and return the first data packet that 
        satisfy the trigger.

        :param fstart: starting frequency in Hz
        :type fstart: float
        :param fstop: ending frequency in Hz
        :type fstop: float
        :param bins: FFT bins requested (number produced likely more)
        :type bins: int
        :param triggers: a class containing trigger information
        :type class:`TriggerSettings`
        :param device_settings: antenna, gain and other device settings
        :type dict:
        """      

        # setup the WSA device
        self.bin_size = bins
        self.fstart = device_set['freq'] - USABLE_BW/2
        self.fstop =  device_set['freq'] + USABLE_BW/2
        self.real_device.apply_device_settings(device_set)
        
        self.real_device.abort()
        self.real_device.flush()
        self.real_device.request_read_perm()
        self._vrt_context = {}

        if self.async_callback:

            
            self.connector.vrt_callback = self.read_data
            self.real_device.capture(bins, 1)

            return

        self.real_device.capture(bins, 1)
        result = None
        while result is None:
            result = self.read_data(self.real_device.read())
        return result
        
    def read_data(self, packet):

        if packet.is_context_packet():
            self._vrt_context.update(packet.fields)
            return
            
        pow_data = compute_fft(self.real_device, packet, self._vrt_context)
        if self.async_callback:
            strt_ind = int(0 + 0.1 * (self.bin_size))
            stp_ind = int(self.bin_size - 0.1 * (self.bin_size))
            self.async_callback(self.fstart, self.fstop, pow_data[strt_ind:stp_ind])
            return
        return (self.fstart, self.fstop, pow_data)
        
        
        
            
        
        

        

