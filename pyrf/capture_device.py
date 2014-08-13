import math

from pyrf.util import compute_usable_bins, adjust_usable_fstart_fstop


class CaptureDeviceError(Exception):
    pass


class CaptureDevice(object):
    """
    Virtual device that returns power levels generated from a single data packet

    :param real_device: device that will will be used for capturing data,
                        typically a :class:`pyrf.thinkrf.WSA` instance.
    :param async_callback: callback to use for async operation (not used if
                           real_device is using a :class:`PlainSocketConnector`)
    :param device_settings: initial device settings to use, passed to
                            :meth:`pyrf.capture_dvice.CaptureDevice.configure_device`
                            if given
    """
    def __init__(self, real_device, async_callback=None, device_settings=None):

        self.real_device = real_device
        if real_device.async_connector():
            if not async_callback:
                raise CaptureDeviceError(
                    "async_callback required for async operation")
            # disable receiving data until we are expecting it
            self.real_device.set_async_callback(None)
        else:
            if async_callback:
                raise CaptureDeviceError(
                    "async_callback not applicable for sync operation")
        self.async_callback = async_callback
        self._configure_device_flag = False
        self._device_set = {}
        if device_settings is not None:
            self.configure_device(device_settings)

    def configure_device(self, device_settings):
        """
        Configure the device settings on the next capture

        :param device_settings: attenuator, decimation frequency shift
                                and other device settings
        :type dict:
        """
        self._configure_device_flag = True
        iq_path = device_settings.get('iq_output_path') 
        if self._device_set.get('iq_output_path') != iq_path or iq_path == 'CONNECTOR':
            self.real_device.apply_device_settings(device_settings)

        for param in device_settings:
            self._device_set[param] = device_settings[param]

        if 'trigger' in self._device_set:
            if self._device_set['trigger']['type'] == 'LEVEL':
                self.real_device.apply_device_settings(self._device_set)

    def capture_time_domain(self, rfe_mode, freq, rbw, device_settings=None,
            min_points=128):
        """
        Initiate a capture of raw time domain IQ or I-only data

        :param rfe_mode: radio front end mode, e.g. 'ZIF', 'SH', ...
        :param freq: center frequency
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

        self.configure_device(dict(
            freq=freq,
            rfe_mode=rfe_mode,
            **(device_settings if device_settings else {}))) 

        if self._configure_device_flag:
            self.real_device.apply_device_settings(self._device_set)
            self._configure_device_flag = False

        full_bw = prop.FULL_BW[rfe_mode]

        self.real_device.abort()
        self.real_device.flush()
        self.real_device.request_read_perm()
        self._vrt_context = {}

        points = round(max(min_points, full_bw / rbw))
        points = 2 ** math.ceil(math.log(points, 2))

        fshift = self._device_set.get('fshift', 0)
        decimation = self._device_set.get('decimation', 1)
        self.usable_bins = compute_usable_bins(prop, rfe_mode, points,
            decimation, fshift)

        if self.async_callback:
            self.real_device.set_async_callback(self.read_data)
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

        rfe_mode = self._device_set['rfe_mode']
        # FIXME: add a "can I tune in this mode?" device property instead
        # of listing modes here
        if rfe_mode in ('DD', 'IQIN'):
            freq = self.real_device.properties.MIN_TUNABLE[rfe_mode]
        else:
            freq = self._device_set['freq']
        decimation = self._device_set.get('decimation', 1)

        self.usable_bins, fstart, fstop = adjust_usable_fstart_fstop(
            self.real_device.properties,
            rfe_mode,
            len(packet.data),
            decimation,
            freq,
            packet.spec_inv,
            self.usable_bins)

        if self.async_callback:
            self.async_callback(fstart, fstop, data)
            return
        return (fstart, fstop, data)
