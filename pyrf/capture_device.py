import math

from pyrf.util import compute_usable_bins, compute_spp_ppb, adjust_usable_fstart_fstop, compute_spp_ppb
from pyrf.vrt import I_ONLY
from pyrf.vrt import DataPacket
import numpy as np

class CaptureDeviceError(Exception):
    pass


class CaptureDevice(object):
    """
    Virtual device that returns power levels generated from a single data packet

    :param real_device: the device that will be used for capturing data,
                        typically a :class:`pyrf.thinkrf.WSA` instance.
    :param async_callback: callback to use for async operation (not used if
                           *real_device* is using a blocking :class:`PlainSocketConnector`)
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
        self.packets_per_block = 1
        self.packets_read = 0
        self.points = 0

    def configure_device(self, device_settings, force_change = False):
        """
        Configure the device settings on the next capture

        :param device_settings: rfe mode, attenuation, decimation and other device settings
        :type device_settings: dict
        :param force_change: force the configuration to apply device_settings changes or not
        :type force_change: bool
        """
        real_func = getattr(self.real_device, "apply_device_settings", None)
        if callable(real_func):
            self.real_device.apply_device_settings(device_settings, force_change)
        for param in device_settings:
            self._device_set[param] = device_settings[param]

    def capture_time_domain(self, rfe_mode, freq, rbw, device_settings=None,
            min_points=256, force_change = False):
        """
        Initiate a capture of raw time domain IQ or I-only data

        :param rfe_mode: radio front end mode, e.g. 'ZIF', 'SH', ...
        :type rfe_mode: string
        :param freq: center frequency in Hz to set
        :type freq: float
        :param rbw: the resolution bandwidth (RBW) in Hz of the data to be captured
                    (output RBW may be smaller than requested)
        :type rbw: float
        :param device_settings: rfe_mode, freq, decimation, fshift and other device settings
        :type device_settings: dict
        :param min_points: smallest number of data points per capture from the device
        :type min_points: int
        :param force_change: force the configuration to apply device_settings changes or not
        :type force_change: bool
        """

        prop = self.real_device.properties
        self.real_device.abort()
        self.real_device.flush()
        self.device_settings = device_settings
        self.real_device.request_read_perm()
        self.configure_device(dict(
            freq=freq,
            rfe_mode=rfe_mode,
            **(device_settings if device_settings else {})), force_change)

        full_bw = prop.FULL_BW[rfe_mode]

        self._vrt_context = {}
        self._data_packets = []

        self.points = round(full_bw / rbw)

        if prop.DEFAULT_SAMPLE_TYPE[rfe_mode] == I_ONLY:
            self.points  *= 2

        self.points = round(max(min_points, self.points))

        self.points, self.packets_per_block = compute_spp_ppb(self.points, prop)

        fshift = self._device_set.get('fshift', 0)
        decimation = self._device_set.get('decimation', 1)
        self.usable_bins = compute_usable_bins(prop, rfe_mode, (self.points * self.packets_per_block),
            decimation, fshift)
        if self.async_callback:
            self.real_device.set_async_callback(self.read_data)
            self.real_device.capture(self.points, self.packets_per_block)

            return

        self.real_device.capture(self.points, self._data_packets)

        result = None
        while result is None:
            result = self.read_data(self.real_device.read())
        return result

    def read_data(self, packet):
        if packet.is_context_packet():
            self._vrt_context.update(packet.fields)
            return
        self.packets_read += 1

        if self.packets_read == 1:
            self.data_packet = packet
        else:
            # if packet type changes, skip packet with a different size
            try:
                self.data_packet.data.np_array = np.concatenate([self.data_packet.data.np_array, packet.data.np_array])
            except ValueError:
                x = 1
        if self.packets_read != self.packets_per_block:

            return

        data= {
            'context_pkt' : self._vrt_context,
            'data_pkt' : self.data_packet}
        self.packets_read = 0

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
            (self.points * self.packets_per_block),
            decimation,
            freq,
            packet.spec_inv,
            self.usable_bins)

        if self.async_callback:
            self.async_callback(fstart, fstop, data)
            return
        return (fstart, fstop, data)
