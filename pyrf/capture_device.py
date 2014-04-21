from pyrf.config import TriggerSettings

import math


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
        for param in device_settings:
            self._device_set[param] = device_settings[param]
        if self._device_set['iq_output_path'] == 'CONNECTOR':
            self.real_device.apply_device_settings(self._device_set)

    def capture_time_domain(self, rbw, device_settings=None, min_points=128):
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

        if device_settings:
            self.configure_device(device_settings)

        if self._configure_device_flag:
            self.real_device.apply_device_settings(self._device_set)
            self._configure_device_flag = False

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

        fshift = self._device_set.get('fshift', 0)
        pass_band_center += fshift / full_bw
        start0 = int((pass_band_center - float(usable_bw) / full_bw / 2)
            * points)
        if rfe_mode != 'ZIF':
            run0 = int(points * float(usable_bw) / full_bw)
            self.usable_bins = [(start0, run0)]
        else:
            dc_offset_bw = prop.DC_OFFSET_BW
            run0 = int(points * (float(usable_bw) - dc_offset_bw)/2 / full_bw)
            start1 = int(math.ceil((pass_band_center + float(dc_offset_bw)
                /2 / full_bw) * points))
            run1 = run0
            self.usable_bins = [(start0, run0), (start1, run1)]
        for i, (start, run) in enumerate(self.usable_bins):
            if start < 0:
                run += start
                start = 0
                self.usable_bins[i] = (start, run)
        if rfe_mode in ('SH', 'HDR', 'SHN'):
            # we're getting only 1/2 the bins
            self.usable_bins = [(x/2, y/2) for x, y in self.usable_bins]
        # XXX usable bins for HDR aren't correct yet, so remove them
        if rfe_mode == 'HDR':
            self.usable_bins = [(0, points)]

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

        # XXX here we "know" that bins = samples/2
        if packet.spec_inv:
            [(start, run)] = self.usable_bins
            start = len(packet.data) / 2 - start - run
            self.usable_bins = [(start, run)]

        if self.async_callback:
            self.async_callback(self.fstart, self.fstop, data)
            return
        return (self.fstart, self.fstop, data)
