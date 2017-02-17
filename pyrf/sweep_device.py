import math
import random
from collections import namedtuple
import time
from pyrf.util import (compute_usable_bins, adjust_usable_fstart_fstop,
    trim_to_usable_fstart_fstop, find_saturation)

import numpy as np

from pyrf.numpy_util import compute_fft

class SweepDeviceError(Exception):
    """
    exception for the sweep device to state an error()
    has occured
    """
    pass

class sweepSettings(object):
    """
    An object used to keep track of the sweep sweep setting
    """

    # sweep entry's start frequency
    fstart = 0.0

    # sweep entry's stop frequency
    fstop = 0.0

    # sweep entry frequency step
    fstep = 0.0
    
    # sweep entry's RFE mode
    rfe_mode = None

    # determine if a second entry is required
    dd_mode = False

    # determines if a non dd entry is needed
    beyound_dd = True

    # entry attenuation
    attenuation = 0

    # entry ppb
    ppb = 1

    # sweep entry's spp
    spp = 0.0

    # sweep capture iterations
    iterations = 0

    # expected spectral points
    spectral_points = 0
class SweepPlanner(object):
    """
    An object that plans a sweep based on  given paramaters.
    """

    def __init__(self, dev_prop):
        self.dev_properties = dev_prop
        self._prev_settings = sweepSettings()

    def plan_sweep(self,fstart,fstop,rbw,mode,dev_settings = {}):
        """
        Plan the sweep given the inputs
        """

        #TODO CHECK FSTART, FSTOP, RBW, AND MODE, make sure they are valid
        self.fstart = fstart
        self.fstop = fstop
        self.rbw = rbw
        self.rfe_mode = mode

        # initialize the sweep settings variable
        sweep_settings = sweepSettings()

        # assign the sweep mode
        sweep_settings.rfe_mode = self.rfe_mode

        if 'attneuator' in dev_settings:
            sweep_settings.attenuation = dev_settings['attenuator']

        # grab the usable bw of the current mode
        self.usable_bw = self.dev_properties.USABLE_BW[self.rfe_mode]

        # calculate the fstart of the sweep entry
        sweep_settings.fstart = self.fstart + (self.usable_bw / 2)


        # determine if DD mode is required
        if self.fstart < self.dev_properties.MIN_TUNABLE[self.rfe_mode]:
            sweep_settings.dd_mode = True
            sweep_settings.fstart = self.dev_properties.MIN_TUNABLE[self.rfe_mode] + (self.usable_bw / 2)

        else:
            sweep_settings.dd_mode = False

        # check if non-dd mode is required

        if self.fstop <= self.dev_properties.MIN_TUNABLE['SH']:
            sweep_settings.beyond_dd = False
        else:
            sweep_settings.beyond_dd = True

        # grab the full banddwidth of the current mode
        full_bw = self.dev_properties.FULL_BW[self.rfe_mode]

        # assign the sweep entry's step frequency, take into account tuning resolution
        sweep_settings.fstep = self.usable_bw - 100E3 #self.dev_properties.TUNING_RESOLUTION

        # calculate the fstop of the sweep entry
        required_steps = math.ceil((self.fstop - sweep_settings.fstart) / self.usable_bw)
        sweep_settings.fstop = sweep_settings.fstart + (required_steps * self.usable_bw)

        # calculate the required samples per packet based on the RBW
        points = full_bw / self.rbw
        sweep_settings.spp = int(32 * round(float(points)/32))

        # calculate the expected number of spectral bins required for the SweepEntry
        sweep_settings.spectral_points = int((self.fstop - self.fstart) / self.rbw)

        self._prev_settings = sweep_settings

        # return the sweep sweep_settings
        return sweep_settings

class SweepDevice(object):
    """
    Virtual device that generates power levels from a range of
    frequencies by sweeping the frequencies with a real device
    and piecing together FFT results.

    :param real_device: device that will will be used for capturing data,
                        typically a :class:`pyrf.devices.thinkrf.WSA` instance.
    :param callback: callback to use for async operation (not used if
                     real_device is using a :class:`PlainSocketConnector`)
    """
    # keep track of the mode
    rfe_mode = None

    # keep track of the fstart/fstop and rbw
    fstart = None
    fstop = None
    rbw = None

    # keep track of non-standard device settings
    device_settings = None

    # keep track of whether DD mode is needed
    dd_mode = False

    # keep track of the sweep settings
    _sweep_settings = None

    # keep track of the packet count
    packet_count = 0

    # array to place spectral data
    spectral_data = []

    def __init__(self, real_device, async_callback=None):

        # initialize the real device
        self.real_device = real_device

        # keep track of the device properties
        self.dev_properties = self.real_device.properties

        # initialize the sweep planner
        self._sweep_planner = SweepPlanner(self.dev_properties)

        # create a sweep id
        self._sweep_id = random.randrange(0, 2**32-1) # don't want 2**32-1

        # make sure user passes async callback if the device has async connector
        if real_device.async_connector():
            if not async_callback:
                raise SweepDeviceError(
                    "async_callback required for async operation")

            # disable receiving data until we are expecting it
            real_device.set_async_callback(None)
        else:

            # make sure user doesnt pass async callback if the connector uses blocking sockets
            if async_callback:
                raise SweepDeviceError(
                    "async_callback not applicable for sync operation")

        self.async_callback = async_callback
        self.continuous = False


    def capture_power_spectrum(self,
                               fstart,
                               fstop,
                               rbw,
                               device_settings=None,
                               mode='SH',
                               continuous=False):
        """
        Initiate a capture of power spectral density by
        setting up a sweep list and starting a single sweep.

        :param fstart: starting frequency in Hz
        :type fstart: float
        :param fstop: ending frequency in Hz
        :type fstop: float
        :param rbw: requested RBW in Hz (output RBW may be smaller than
                    requested)
        :type rbw: float
        :param device_settings: antenna, gain and other device settings
        :type dict:
        :param mode: sweep mode, 'ZIF', 'SH', or 'SHN'
        :type mode: string
        :param continuous: do a sweep with the same config as before
        :type continuous: bool
        :param min_points: smallest number of points per capture from real_device
        :type min_points: int
        """

        if continuous and not self.async_callback:
            raise SweepDeviceError(
                "continuous mode only applies to async operation")

        self.real_device.flush()
        self.real_device.abort()
        self.real_device.request_read_perm()

        # grab the device settings
        self.device_settings = device_settings
        # keep track of the mode
        self.rfe_mode = mode

        # grab the usable bw of the current mode
        self.usable_bw = self.dev_properties.USABLE_BW[self.rfe_mode]

        # keep track if this is a continoued swee
        self.continuous = continuous

        # keep track of the fstart/fstop and rbw
        self.fstart = fstart
        self.fstop = fstop
        self.rbw = rbw

        # TODO Check if continuous is requested
        self.real_device.sweep_clear()

        # plan the sweep
        self._sweep_settings = self._sweep_planner.plan_sweep(self.fstart,
                                                              self.fstop,
                                                              self.rbw,
                                                              self.rfe_mode,
                                                              self.device_settings)

        # configure the device with the sweep sweep_settings
        self.real_device.sweep_add(self._sweep_settings)

        # configure the iteration
        self.real_device.sweep_iterations(1)

        # capture the sweep data
        return self._perform_full_sweep()

    def _perform_full_sweep(self):

        # perform the sweep using async socket
        if self.async_callback:

            # set the async callback
            self.real_device.set_async_callback(self._vrt_receive)

            # start the sweep sequence
            self._start_sweep()
            return

        # perform sweep using blocking sockets
        self._start_sweep()
        result = None
        while result is None:
            result = self._vrt_receive(self.real_device.read())

        return result

    def _start_sweep(self):

        self._vrt_context = {}
        self.spectral_data = []
        self.got_id = False
        # keep track of packets recieved
        self.packet_count = 0

        self.real_device.sweep_start()

    def _vrt_receive(self, packet):
        packet_bytes = packet.size * 4

        # if the packet is a context packet
        if packet.is_context_packet():
            self._vrt_context.update(packet.fields)
            return


        # check to see if we recieved our sweep ID
        if 'sweepid' in self._vrt_context:
            self.got_id = True

        # if no ID recieved, then continue
        if not self.got_id:
            return

        # increment the packet count
        self.packet_count += 1

        # compute the fft
        pow_data = compute_fft(self.real_device, packet, self._vrt_context)

        # check if DD mode was used in this sweep
        if self.packet_count == 1 and self._sweep_settings.dd_mode:
            # calculate where the start bin should start
            start_bin = int(len(pow_data) * (self.fstart / self.dev_properties.FULL_BW['DD']))

            # calculate the stop bin
            stop_bin = int(len(pow_data) * (self.dev_properties.MIN_TUNABLE['SH'] / self.dev_properties.FULL_BW['DD']))

            # check if the only mode used was DD mode
            if self.fstop <= self.dev_properties.MIN_TUNABLE[self.rfe_mode]:

                stop_bin =  int(len(pow_data) * (self.fstop / self.dev_properties.FULL_BW['DD']))

                # if there was only DD mode, append spectral data and send to client
                self.spectral_data = pow_data[start_bin:stop_bin]

                return self._emit_data()

            self.spectral_data = pow_data[start_bin:stop_bin]
            return

        packet_freq = self._vrt_context['rffreq']

        packet_start = packet_freq - (self.usable_bw / 2)
        packet_stop = packet_freq + (self.usable_bw / 2)

        # determine the usable bins in this config
        usable_bins = compute_usable_bins(self.dev_properties,
                                          self.rfe_mode,
                                          self._sweep_settings.spp,
                                          1,
                                          0)

        # adjust the usable range based on spectral inversion
        usable_bins, start, stop = adjust_usable_fstart_fstop(self.dev_properties,
                                                              self.rfe_mode,
                                                              len(pow_data) * 2,
                                                              1,
                                                              packet_freq,
                                                              packet.spec_inv,
                                                              usable_bins)

        #trim the FFT data, note decimation is 1, fshift is 0
        trimmed_spectrum, edge_data, fstart, fstop = trim_to_usable_fstart_fstop(pow_data,
                                                                                 usable_bins,
                                                                                 packet_start,
                                                                                 packet_stop)
                                                    
        # check if this is the last expected packet
        if self.fstop <= packet_freq + (self.usable_bw / 2):
            # calculate the stop bin
            stop_bin = int(len(trimmed_spectrum) * ((self.fstop - packet_start) / self.usable_bw))

            # take spectral inversion into account
            if packet.spec_inv:
                stop_bin = len(trimmed_spectrum) - stop_bin

            self.spectral_data = np.concatenate([self.spectral_data, trimmed_spectrum[:stop_bin]])
            # send the data to the client
            return self._emit_data()

        else:
            self.spectral_data = np.concatenate([self.spectral_data, trimmed_spectrum])

            return


    def _emit_data(self):
        # emit the data to the client

        # if async callback is available, emit the data
        if self.async_callback:
            self.real_device.vrt_callback = None
            self.async_callback(self.fstart, self.fstop, self.spectral_data)
            return
        # return the values if using blocking sockets
        else:
            return (self.fstart, self.fstop, self.spectral_data)
