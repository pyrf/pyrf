import sys
import math
import random
from collections import namedtuple
import time
from pyrf.util import (compute_usable_bins, adjust_usable_fstart_fstop,
    trim_to_usable_fstart_fstop, find_saturation)

import numpy as np

from pyrf.numpy_util import compute_fft

MAXIMUM_SPP = 32768

class SweepDeviceError(Exception):
    """
    exception for the sweep device to state an error()
    has occured
    """
    pass

class SweepSettings(object):
    """
    An object used to keep track of the sweep sweep setting
    """

    def __init__(self):
        # start frequency of the results we will eventually return
        self.bandstart = 0.0

        # stop frequency of the results we will eventually return
        self.bandstop = 0.0

        # sweep entry's start frequency
        self.fstart = 0.0

        # sweep entry's stop frequency
        self.fstop = 0.0

        # sweep entry frequency step
        self.fstep = 0.0
        
        # sweep entry's RFE mode
        self.rfe_mode = None

        # determine if a second entry is required
        self.dd_mode = False

        # determines if a non dd entry is needed
        self.beyond_dd = True

        # entry attenuation
        self.attenuation = 0

        # entry ppb
        self.ppb = 1

        # sweep entry's spp
        self.spp = 0.0

        # sweep capture iterations
        self.iterations = 0

        # expected spectral points
        self.spectral_points = 0

        # determines if a sweep entry is required at the end
        self.make_end_entry = False
        
        # determine the frequency of the end entry
        self.end_entry_freq = 0.0

        # how many steps are in this sweep
        self.step_count = 0

        # what's the actual RBW of what we're capturing
        self.rbw = 0

    def __str__(self):
        return "SweepSettings[ bandstart = %d, bandstop = %d, fstart = %d, fstop = %d, fstep = %d, step_count = %d, rfe_mode = %s, dd_mode = %s, beyond_dd = %s, attenuation = %s, ppb = %d, spp = %d, iterations = %d, spectral_points = %d, make_end_entry = %s, end_entry_freq = %d, rbw = %f ]" % (self.bandstart, self.bandstop, self.fstart, self.fstop, self.fstep, self.step_count, self.rfe_mode, self.dd_mode, self.beyond_dd, self.attenuation, self.ppb, self.spp, self.iterations, self.spectral_points, self.make_end_entry, self.end_entry_freq, self.rbw)


class SweepPlanner(object):
    """
    An object that plans a sweep based on  given paramaters.
    """

    def __init__(self, dev_prop):
        self.dev_properties = dev_prop
        self._prev_settings = SweepSettings()

    def plan_sweep(self, fstart, fstop, rbw, mode, dev_settings = {}):
        """
        Plan the sweep given the inputs
        """

        # initialize the sweep settings variable
        sweep_settings = SweepSettings()

        # assign the sweep mode and start/stop
        sweep_settings.rfe_mode = mode
        sweep_settings.bandstart = fstart
        sweep_settings.bandstop = fstop

        if 'attenuator' in dev_settings:
            sweep_settings.attenuation = dev_settings['attenuator']

        # grab the usable bw of the current mode
        usable_bw = self.dev_properties.USABLE_BW[mode]

        # calculate fstart frequency
        if fstart < self.dev_properties.MIN_TUNABLE[mode]:
            sweep_settings.dd_mode = True
            sweep_settings.fstart = self.dev_properties.MIN_TUNABLE[mode] + (usable_bw / 2)
            sweep_settings.step_count += 1

        else:
            sweep_settings.dd_mode = False
            sweep_settings.fstart = fstart + (usable_bw / 2)

            # reduce fstart by a bit to account for floating point errors
            # TODO: make this based off rbw and tuning resolution, instead of a magic number
            sweep_settings.fstart -= 100e3

        # check if non-dd mode is required
        if fstop <= self.dev_properties.MIN_TUNABLE[mode]:
            sweep_settings.beyond_dd = False
        else:
            sweep_settings.beyond_dd = True

            # assign the sweep entry's step frequency, take into account tuning resolution
            sweep_settings.fstep = usable_bw - 100E3 #self.dev_properties.TUNING_RESOLUTION

            # calculate the fstop of the sweep entry from fstart and how many usable_bw's we need
            fspan = fstop - (sweep_settings.fstart - (usable_bw / 2))
            required_steps = math.ceil(fspan / sweep_settings.fstep)
            sweep_settings.fstop = sweep_settings.fstart + (required_steps * sweep_settings.fstep)
            sweep_settings.step_count += required_steps

        # make sure fstop is lower than max tunable
        # - it can sometimes be higher if an fstart is chosen, such that our 
        #   fstep causes our fstop to go beyond fmax to cover all the band required
        sweep_settings.make_end_entry = False
        if sweep_settings.fstop > self.dev_properties.MAX_TUNABLE[mode]:
            # go back one step
            sweep_settings.fstop -= sweep_settings.fstep

            # add an entry for fmax
            sweep_settings.make_end_entry = True
            sweep_settings.end_entry_freq = self.dev_properties.MAX_TUNABLE[mode] - (usable_bw / 2)

        # calculate the required SPP to get the RBW desired
        sweep_settings.spp = self.dev_properties.FULL_BW[mode] / rbw

        # find closest multiple of 32 because hardware
        sweep_settings.spp = int(32 * round(float(sweep_settings.spp) / 32))

        # double the points for SH/SHN mode
        if mode in ['SH', 'SHN']:
            sweep_settings.spp = sweep_settings.spp * 2

        # if we're using zif mode, but we have a DD entry, we have half the SPP avaible, since DD is I-only and ZIF is IQ
        if (mode == 'ZIF') and sweep_settings.dd_mode:
            maxspp = self.dev_properties.MAX_SPP / 2
        else:
            maxspp = self.dev_properties.MAX_SPP

        # adjust SPP if it's too big
        sweep_settings.spp = min(maxspp, sweep_settings.spp)

        # figure out our actual RBW (account for real vs complex data)
        sweep_settings.rbw = self.dev_properties.FULL_BW[mode] / sweep_settings.spp
        if not (mode == 'ZIF'):
            sweep_settings.rbw = sweep_settings.rbw * 2

        # calculate the expected number of spectral bins required for the SweepEntry
        sweep_settings.spectral_points = int(round((sweep_settings.bandstop - sweep_settings.bandstart) / sweep_settings.rbw))

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

    # determine if a new entry is required
    _new_entry = True

    # array to place spectral data
    spectral_data = []

    capture_count = 0
    def __init__(self, real_device, async_callback=None):

        # init log string
        self.logstr = ''
        self.logtype = 'NONE'

        # initialize the real device
        self.real_device = real_device

        # request read permission from device
        self.real_device.request_read_perm()

        # keep track of the device properties
        self.dev_properties = self.real_device.properties

        # initialize the sweep planner
        self._sweep_planner = SweepPlanner(self.dev_properties)

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

        # init the sweep id
        self._sweep_id = 0

        # init last finished (technically, it hasn't finished, but for our purposes, it has)
        self._last_finished = True

    def log(self, firstmsg, *msgs):
        if self.logtype == 'LOG':
            self.logstr += firstmsg.__str__()
            for msg in msgs:
                self.logstr += ", "
                self.logstr += msg.__str__()
            self.logstr += "\n"
        elif self.logtype == 'PRINT':
            sys.stdout.write(firstmsg.__str__())
            for msg in msgs:
                sys.stdout.write(", ")
                sys.stdout.write(msg.__str__())
            sys.stdout.write("\n")


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
        - This function does not pipeline, and if the last sweep isn't
          received before starting a new one, it will generate a failure

        :param fstart: starting frequency in Hz
        :type fstart: float
        :param fstop: ending frequency in Hz
        :type fstop: float
        :param rbw: requested RBW in Hz (output RBW may be smaller than
                    requested)
        :type rbw: float
        :param device_settings: attenuation and other settings
        :type dict:
        :param mode: sweep mode, 'ZIF', 'SH', or 'SHN'
        :type mode: string
        :param continuous: do a sweep with the same config as before
        :type continuous: bool
        """

        self.log("- capture_power_spectrum", fstart, fstop, rbw, device_settings, mode, continuous)
        
        if continuous and not self.async_callback:
            raise SweepDeviceError(
                "continuous mode only applies to async operation")
 
        # see if the last sweep has finished
        if not self._last_finished:
            raise SweepDeviceError(
                "previous sweep must have finished before starting a new one")
        self._last_finished = False

        # increment the sweep id
        if self._sweep_id < 0x00000000ffffffff:
            self._sweep_id += 1
        else:
            self._sweep_id = 0
            
        # keep track if this is a continoued swee
        self.continuous = continuous

        # plan the sweep
        self._sweep_settings = self._sweep_planner.plan_sweep(fstart, fstop, rbw, mode, device_settings)
        self.log("self._sweep_settings = %s" % self._sweep_settings)

        # remember our last sweep for optimization purposes
        self._last_sweep = (fstart, fstop, rbw, mode, device_settings, continuous)

        # configure the device with the sweep sweep_settings
        self.real_device.sweep_clear()
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

        # initialize the array we'll use to hold results
        self.spectral_data = np.zeros(self._sweep_settings.spectral_points)

        # keep track of packets recieved
        self.packet_count = 0

        self.real_device.sweep_start(self._sweep_id)

    def _vrt_receive(self, packet):

        # context packet just update our context dictionary
        if packet.is_context_packet():
            self._vrt_context.update(packet.fields)
            self.log(packet)
            return

        # check to see if we recieved our sweep ID
        if not ('sweepid' in self._vrt_context):
            return

        # increment the packet count
        self.packet_count += 1
        self.log("#%d of %d - %s" % (self.packet_count, self._sweep_settings.step_count, packet))

        # compute the fft
        pow_data = compute_fft(self.real_device, packet, self._vrt_context)

        # check if DD mode was used in this sweep
        if self.packet_count == 1 and self._sweep_settings.dd_mode:
            # copy the data into the result array
            self._copy_data(0, self.dev_properties.FULL_BW['DD'], pow_data, self._sweep_settings.bandstart, self._sweep_settings.bandstop, self.spectral_data);

            if self._sweep_settings.beyond_dd:
                return
            else:
                return self._emit_data()

        # retrieve the frequency and usable BW of the packet
        packet_freq = self._vrt_context['rffreq']
        usable_bw = self.dev_properties.USABLE_BW[self._sweep_settings.rfe_mode]

        # calc rbw for this packet
        rbw = float(self.dev_properties.FULL_BW[self._sweep_settings.rfe_mode]) / len(pow_data)
        self.log("rbw = %f, %f" % (rbw, self._sweep_settings.rbw))

        # determine the usable bins in this config
        self.log("===> compute_usable_bins()", self._sweep_settings.rfe_mode, self._sweep_settings.spp, 1, 0)
        usable_bins = compute_usable_bins(self.dev_properties,
                                          self._sweep_settings.rfe_mode,
                                          self._sweep_settings.spp,
                                          1,
                                          0)
        self.log("<--- usable_bins", usable_bins)

        # adjust the usable range based on spectral inversion
        self.log("===> adjust_usable_fstart_fstop()", "self.dev_properties", self._sweep_settings.rfe_mode, len(pow_data) * 2, 1, packet_freq, packet.spec_inv, usable_bins)
        usable_bins, packet_start, packet_stop = adjust_usable_fstart_fstop(self.dev_properties,
                                                              self._sweep_settings.rfe_mode,
                                                              len(pow_data) * 2,
                                                              1,
                                                              packet_freq,
                                                              packet.spec_inv,
                                                              usable_bins)
        self.log("<--- adjust_usable_fstart_fstop", packet_start, packet_stop, usable_bins)
        #
        # WARNING: the start and stop returned from this function are HIGHLY sketchy
        #

        # calculate packet frequency range
        #packet_start = packet_freq - (self.dev_properties.FULL_BW[self._sweep_settings.rfe_mode] / 2)
        #packet_stop = packet_freq + (self.dev_properties.FULL_BW[self._sweep_settings.rfe_mode] / 2)
        #print "packet start/stop", packet_start, packet_stop

        #trim the FFT data, note decimation is 1, fshift is 0
        self.log("===> trim_to_usable_fstart_fstop()", "pow_data", usable_bins, packet_start, packet_stop)
        trimmed_spectrum, edge_data, usable_start, usable_stop = trim_to_usable_fstart_fstop(pow_data,
                                                                                 usable_bins,
                                                                                 packet_start,
                                                                                 packet_stop)
        self.log("<--- trim_to_usable_fstart_fstop", usable_start, usable_stop, "trimmed_spectrum", edge_data)

        # copy the data
        self._copy_data(usable_start, usable_stop, trimmed_spectrum, self._sweep_settings.bandstart, self._sweep_settings.bandstop, self.spectral_data);

        # if there's no more packets, emit result
        if self.packet_count == self._sweep_settings.step_count:
            return self._emit_data()

        # all done
        return


    def _emit_data(self):

        # note that we finished this sweep
        self._last_finished = True

        # if async callback is available, emit the data
        if self.async_callback:

            self.async_callback(self._sweep_settings.bandstart, self._sweep_settings.bandstop, self.spectral_data)
            return
        # return the values if using blocking sockets
        else:
            return (self._sweep_settings.bandstart, self._sweep_settings.bandstop, self.spectral_data)


    def _copy_data(self, src_fstart, src_fstop, src_psd, dst_fstart, dst_fstop, dst_psd):
        self.log("_copy_data(%d, %d, src_psd, %d, %d, dst_psd)" % (src_fstart, src_fstop, dst_fstart, dst_fstop))

        # calc src len and dst len
        srclen = len(src_psd)
        dstlen = len(dst_psd)
        self.log("len -- src = %d, dst = %d" % (srclen, dstlen))

        # calc src and dest rbw
        srcrbw = (src_fstop - src_fstart) / srclen
        dstrbw = (dst_fstop - dst_fstart) / dstlen
        self.log("rbw = %f, %f, %f" % (srcrbw, dstrbw, self._sweep_settings.rbw))

        # check if packet start is before sweep start.  shouldn't happen, but check anyway
        self.log("boundary(start) = %f / %f" % (src_fstart, dst_fstart))
        if src_fstart < dst_fstart:
            self.log("foo")
            src_start_bin = int((dst_fstart - src_fstart) / srcrbw)
        else:
            self.log("bar")
            src_start_bin = 0

        # check if packet stop is after sweep stop.  this means we don't need the whole packet
        self.log("boundary(stop) = %f / %f" % (src_fstop, dst_fstop))
        if src_fstop > dst_fstop:
            self.log("foo")
            src_stop_bin = srclen - int((src_fstop - dst_fstop) / srcrbw)
        else:
            self.log("bar")
            src_stop_bin = srclen

        # how many values are we copying?
        tocopy = src_stop_bin - src_start_bin

        # calculate dest start index
        if src_fstart < dst_fstart:
            dst_start_bin = 0
        else:
            dst_start_bin = int(round((src_fstart - dst_fstart) / dstrbw))

        # calculate dest stop index
        dst_stop_bin = dst_start_bin + tocopy
        if dst_stop_bin > dstlen:
            dst_stop_bin = dstlen

            # adjust tocopy
            tocopy = dst_stop_bin - dst_start_bin

            # adjust src stop bin because we adjusted tocopy
            src_stop_bin = src_start_bin + tocopy

        # copy the data
        self.log("dst_psd[%d:%d] = src_psd[%d:%d]" % (dst_start_bin, dst_stop_bin, src_start_bin, src_stop_bin))
        dst_psd[dst_start_bin:dst_stop_bin] = src_psd[src_start_bin:src_stop_bin]
