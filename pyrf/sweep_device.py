import sys
import math
import random
from collections import namedtuple
import time
from pyrf.util import (compute_usable_bins, adjust_usable_fstart_fstop,
    trim_to_usable_fstart_fstop, find_saturation)

import numpy as np
from twisted.internet import defer

from pyrf.numpy_util import compute_fft
import struct
MAXIMUM_SPP = 32768


class correction_vector_acquire(object):
    data_buffer = ""
    v_type = "SIGNAL"
    dut = None
    complete_buffer = False
    d = None
    offset = 0
    size = 0
    transfer_size = 16*1024

    def get_vector_loop(self, data):
        self.data_buffer = b"".join([self.data_buffer, data])
        self.offset += len(data)
        if self.offset >= self.size:
            # we have gotten all out data, return this object
            if self.d is not None:
                self.d.callback(self)
        else:
            # more data, grab another set of data
            data1 = self.dut.correction_data(self.v_type, self.offset,
                                             self.transfer_size)
            # and add this function to the call back
            data1.addCallback(self.get_vector_loop)

    def get_vector_data(self, size):
        # We got out size
        if size is None:
            # size is return None threw our created deffered in get_vector
            if self.d is not None:
                self.d.callback(None)
            return

        self.size = int(size)
        if self.size == 0:
            if self.d is not None:
                self.d.callback(None)
            return

        if self.size < self.transfer_size:
            self.transfer_size = self.size
        # Grab our first set of data (deffered)
        data = self.dut.correction_data(self.v_type, self.offset,
                                        self.transfer_size)
        # add the self.get_vector_loop call back
        data.addCallback(self.get_vector_loop)
        # what happens to error back here?

    def error_b(self, failure):
        if self.d is not None:
            self.d.callback(None)
        return None

    def get_vector(self, v_type=None):
        #
        self.v_type = v_type
        self.offset = 0
        self.data_buffer = ""
        # Create a defered
        d = defer.Deferred()
        self.d = d

        # get our size (deffered)
        size = self.dut.correction_size(self.v_type)
        size.addCallback(self.get_vector_data)
        size.addErrback(self.error_b)
        # return our deferred
        return d


class correction_vector(object):
    correction_vectors = None
    frequency_index = None
    digest = None

    def __init__(self):
        self.frequency_index = []
        self.dy = np.dtype(np.int32)
        self.dy = self.dy.newbyteorder('>')
        self.correction_vectors = {}

    def _binary_search(self, freq):
        # Simple binary search, modified to work the object's datastructure
        lo = 0
        hi = len(self.frequency_index)
        while lo < hi:
            mid = (lo + hi) // 2
            if self.frequency_index[mid][0] * 1e3 < freq:
                lo = mid + 1
            else:
                hi = mid
        return lo

    def _interp(self, in_array, number_of_points):
        # array index of our orignal from 0 to size of vector - 1
        x = np.arange(0.0, self.vector_size, 1.0)
        # our new index
        z = np.linspace(0.0, self.vector_size - 1, number_of_points)
        # interpolate to get our new vector array
        out_array = np.interp(z, x, in_array)
        return out_array

    def get_correction_vector(self, freq, number_of_points):
        # binary search, retunrs our index
        index = self._binary_search(freq)
        # get the case where we go off the end
        if index == len(self.frequency_index):
            index = index - 1

        # get our vector
        vector = self.correction_vectors[self.frequency_index[index][1]]
        # convert from micro db to db
        vector = vector / 1000000.0
        # interpolate our vector to the wanted size
        resampled_vector = self._interp(vector, number_of_points)
        return resampled_vector

    def buffer_to_vector(self, buffer_in):
        if buffer_in is None:
            raise ValueError

        if len(buffer_in) < 8 + 40:
            raise ValueError

        # Get the first 8 bytes
        offset = 0
        size = 8
        input_buffer = buffer_in[offset:offset + size]
        version, freq_num, vector_num, self.vector_size = struct.unpack("!HHHH", input_buffer)
        offset = size

        # Ignore the next 40 bytes, as not used know
        offset += 40

        # grab our frequency list
        size = 6 * freq_num
        input_buffer = buffer_in[offset:offset + size]
        offset += size

        if len(input_buffer) < size:
            raise ValueError
        # loop over our buffer, adding a frequency pair to the array
        for i in range(freq_num):
            freq, index = struct.unpack("!LH", input_buffer[i*6:i*6+6])
            self.frequency_index.append([freq, index])

        # grab our correction vectors
        for i in range(vector_num):

            # Grab out index
            size = 2
            input_buffer = buffer_in[offset:offset + size]
            index = struct.unpack(">H", input_buffer)[0]
            offset += size

            # get our correction vector
            size = 4 * self.vector_size
            input_buffer = buffer_in[offset:offset + size]
            micro_db = np.frombuffer(input_buffer, dtype=self.dy,
                                     count=self.vector_size)
            self.correction_vectors[index] = micro_db
            offset += size


class SweepDeviceError(Exception):
    """
    Exception for the sweep device to state an error() has occured
    """
    pass

class SweepSettings(object):
    """
    An object used to keep track of the sweep settings
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

    :param dev_prop: the sweep device properties
    :type dev_prop: dict
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

        # make sure our result is atleast 1 RBW big
        if (sweep_settings.bandstop - sweep_settings.bandstart) < sweep_settings.rbw:
            fstop = sweep_settings.bandstart + sweep_settings.rbw
            sweep_settings.bandstop = fstop

        # change fstart and stop by a bit to account for floating point errors
        # TODO: make this take into account tuning resolution
        fstart -= sweep_settings.rbw * 4
        fstop += sweep_settings.rbw * 4

        # calculate fstart frequency
        if fstart < self.dev_properties.MIN_TUNABLE[mode]:
            sweep_settings.dd_mode = True
            sweep_settings.fstart = self.dev_properties.MIN_TUNABLE[mode] + (usable_bw / 2)
            sweep_settings.step_count += 1

        # make sure we don't accidentally make an fstart that's beyond our tuning range
        elif (fstart + (usable_bw / 2)) > self.dev_properties.MAX_TUNABLE[mode]:
            sweep_settings.dd_mode = False
            sweep_settings.fstart = self.dev_properties.MAX_TUNABLE[mode] - (usable_bw / 2)

        else:
            sweep_settings.dd_mode = False
            sweep_settings.fstart = fstart + (usable_bw / 2)

        # check if non-dd mode is required
        if fstop <= self.dev_properties.MIN_TUNABLE[mode]:
            sweep_settings.beyond_dd = False
        else:
            sweep_settings.beyond_dd = True
            sweep_settings.step_count += 1

            # assign the sweep entry's step frequency reducing by a couple rbw to account for floating point errors
            # TODO: make this take into account tuning resolution
            sweep_settings.fstep = usable_bw - (sweep_settings.rbw * 4)

            # calculate the fstop of the sweep entry from fstart and how many usable_bw's we need
            fspan = fstop - sweep_settings.fstart - sweep_settings.rbw
            required_steps = round(fspan / sweep_settings.fstep)
            sweep_settings.fstop = sweep_settings.fstart + (required_steps * sweep_settings.fstep)
            sweep_settings.step_count += required_steps

        # make sure fstop is lower than max tunable
        # - it can sometimes be higher if an fstart is chosen, such that our
        #   fstep causes our fstop to go beyond fmax to cover all the band required
        sweep_settings.make_end_entry = False
        sweep_settings.end_entry_freq = 0
        if sweep_settings.fstop > self.dev_properties.MAX_TUNABLE[mode]:
            # go back one step
            sweep_settings.fstop -= sweep_settings.fstep

            # add an entry for fmax
            sweep_settings.make_end_entry = True
            sweep_settings.end_entry_freq = self.dev_properties.MAX_TUNABLE[mode] - (usable_bw / 2)

        # calculate the expected number of spectral bins required for the SweepEntry
        sweep_settings.spectral_points = int(round((sweep_settings.bandstop - sweep_settings.bandstart) / sweep_settings.rbw))

        # return the sweep_settings
        return sweep_settings


class SweepDevice(object):
    """
    Virtual device that generates power spectrum from a given frequency range
    by sweeping the frequencies with a real device and piecing together the FFT results.

    :param real_device: the RF device that will be used for capturing data,
                        typically a :class:`pyrf.devices.thinkrf.WSA` instance.
    :param async_callback: a callback to use for async operation (not used if
                     *real_device* is using a blocking :class:`PlainSocketConnector`)
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

    correction_thresh = 10

    sp_corr_obj = None
    nf_corr_obj = None

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

        # initialize the geolocation callback
        self._geo_callback_func = None
        self._geo_callback_data = None

        # initialize the sweep planner
        self._sweep_planner = SweepPlanner(self.dev_properties)

        # make sure user passes async callback if the device has async connector
        if real_device.async_connector():
            if not async_callback:
                raise SweepDeviceError(
                    "async_callback required for async operation")

            # disable receiving data until we are expecting it
            real_device.set_async_callback(None)

            # Function to be called when async data is done capturing
            def _save_correction_vector(data_buffer):
                if data_buffer is None:
                    return None
                try:
                    if data_buffer.v_type == "SIGNAL":
                        self.sp_corr_obj = correction_vector()
                        self.sp_corr_obj.buffer_to_vector(data_buffer.data_buffer)
                    elif data_buffer.v_type == "NOISE":
                        self.nf_corr_obj = correction_vector()
                        self.nf_corr_obj.buffer_to_vector(data_buffer.data_buffer)
                except AttributeError:
                    if data_buffer.v_type == "SIGNAL":
                        self.sp_corr_obj = None
                    elif data_buffer.v_type == "NOISE":
                        self.nf_corr_obj = None

            # function to catch the errback of the async code. Used to handle
            # the case when we can get the correction vectors.
            def _catch_timeout(failure):
                failure.trap(IOError)
                return None

            vector_obj = correction_vector_acquire()
            vector_obj.dut = real_device

            vector_obj1 = correction_vector_acquire()
            vector_obj1.dut = real_device

            d1 = vector_obj.get_vector("NOISE")
            d1.addCallback(_save_correction_vector)
            d1.addErrback(_catch_timeout)

            d2 = vector_obj1.get_vector("SIGNAL")
            d2.addCallback(_save_correction_vector)
            d2.addErrback(_catch_timeout)

        else:

            # make sure user doesnt pass async callback if the connector uses blocking sockets
            if async_callback:
                raise SweepDeviceError(
                    "async_callback not applicable for sync operation")

            def _get_correction(dut, v_type=None):
                if v_type.upper() == "SIGNAL" or v_type.upper() == "NOISE":
                    v_type = v_type.upper()
                else:
                    raise ValueError

                max_buf_size = 16*1024
                offset = 0
                bin_data = ""
                try:
                    signal_size = dut.correction_size(v_type)
                except (IOError, OSError):  # this will handle socket.error's
                    raise ValueError

                # We have nothing to transfer
                if signal_size == 0:
                    return None

                # check to see if tere is more data than can be transfer in one
                # go
                if signal_size > max_buf_size:
                    # if so transfer our max buffer size
                    transfer_size = max_buf_size
                else:
                    # if not grab only what we need
                    transfer_size = signal_size

                # While we still have data remaining
                while offset < signal_size:
                    # get the data
                    data_buffer = dut.correction_data(v_type, offset,
                                                      transfer_size)
                    # figure out how many bytes were transfered
                    transfered = len(data_buffer)
                    # append the data to the buffer of what we have allready
                    # got
                    bin_data = b"".join([bin_data, data_buffer])
                    # increase the offset
                    offset = offset + transfered
                return bin_data

            self.sp_corr_obj = correction_vector()
            try:
                self.sp_corr_obj.buffer_to_vector(_get_correction(self.real_device, "SIGNAL"))
            except ValueError:
                self.sp_corr_obj = None

            self.nf_corr_obj = correction_vector()
            try:
                self.nf_corr_obj.buffer_to_vector(_get_correction(self.real_device, "NOISE"))
            except ValueError:
                self.nf_corr_obj = None

        self.async_callback = async_callback
        self.continuous = False

        # init the sweep id
        self._next_sweep_id = 0

        # init last finished (technically, it hasn't finished, but for our purposes, it has)
        self._last_finished = True

    # Private function
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


    def set_geolocation_callback(self, func, data = None):
        """
        set a callback that will get called whenever the geolocation information
        of the device is updated.
        The callback function should accept two parameters.  The first parameter
        will be the callback data that was passed in this function
        set_geolocation_callback(func, data, geolocation_dictionary).
        The geolocation_dictionary will have the following properties:
        - oui
        - seconds
        - altitude
        - longitude
        - speedoverground
        - secondsfractional
        - track
        - latitude
        - magneticvariation
        - heading
        See the programmer's guide for usage on each of these properties.

        :param func: the function to be called
        :param data: the data to be passed to the function
        :returns: None
        """

        self._geo_callback_func = func
        self._geo_callback_data = data


    def capture_power_spectrum(self,
                               fstart,
                               fstop,
                               rbw,
                               device_settings=None,
                               mode='SH',
                               continuous=False):
        """
        Initiate a data capture from the *real_device* by setting up a sweep list
        and starting a single sweep, and then return power spectral density data
        along with the **actual** sweep start and stop frequencies set (which
        might not be exactly the same as the requested *fstart* and *fstop*).

        .. note:: This function does not pipeline, and if the last sweep isn't received before starting a new one, it will generate a failure.

        :param int fstart: sweep starting frequency in Hz
        :param int fstop: sweep ending frequency in Hz
        :param float rbw: the resolution bandwidth (RBW) in Hz of the data to be captured (output RBW may be smaller than requested)
        :param device_settings: attenuation and other device settings
        :type device_settings: dict
        :param str mode: sweep mode, 'ZIF', 'SH', or 'SHN'
        :param bool continuous: set sweep to be continuously or not (once only)

        :returns: fstart, fstop, power_data
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
        if self._next_sweep_id < 0x00000000ffffffff:
            self._next_sweep_id += 1
        else:
            self._next_sweep_id = 0

        # keep track if this is a continuous sweep
        self.continuous = continuous

        # plan the sweep
        self._sweep_planner = SweepPlanner(self.dev_properties)
        self._sweep_settings = self._sweep_planner.plan_sweep(fstart, fstop, rbw, mode, device_settings)
        self.log("self._sweep_settings = %s" % self._sweep_settings)

        # remember our last sweep for optimization purposes
        self._last_sweep = (fstart, fstop, rbw, mode, device_settings, continuous)

        # configure the device with the sweep_settings
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

        self.real_device.sweep_start(self._next_sweep_id)

    def _vrt_receive(self, packet):

        # context packet just update our context dictionary
        if packet.is_context_packet():
            # look for any geolocation info
            geo = { }
            for field in [ 'latitude', 'longitude', 'altitude', 'speedoverground', 'heading', 'track', 'magneticvariation' ]:
                if field in packet.fields:
                    geo[field] = packet.fields[field]
            if geo and self._geo_callback_func:
                # execute callback
                func = self._geo_callback_func
                func(self._geo_callback_data, geo)

            self._vrt_context.update(packet.fields)
            self.log(packet)
            return

        # check to see if we recieved our sweep ID
        if not ('sweepid' in self._vrt_context):
            return

        # make sure we are receiving packets for the right sweep
        if not (self._vrt_context['sweepid'] == self._next_sweep_id):
            raise SweepDeviceError("data packets received before start of sweep received!  cur = %d, next = %d" % (self._vrt_context['sweepid'], self._next_sweep_id))

        # increment the packet count
        self.packet_count += 1
        self.log("#%d of %d - %s" % (self.packet_count, self._sweep_settings.step_count, packet))

        # retrieve the frequency and usable BW of the packet
        packet_freq = self._vrt_context['rffreq']
        usable_bw = self.dev_properties.USABLE_BW[self._sweep_settings.rfe_mode]

        # compute the fft
        pow_data = compute_fft(self.real_device, packet, self._vrt_context)

        # calc rbw for this packet
        rbw = float(self.dev_properties.FULL_BW[self._sweep_settings.rfe_mode]) / len(pow_data)
        self.log("rbw = %f, %f" % (rbw, self._sweep_settings.rbw))

        # Check if we are above 50 MHz and in SH mode
        if packet_freq >= 50e6 and self._sweep_settings.rfe_mode == "SH":
            number_of_points = len(pow_data)
            # check if we have correction vectors (Noise)
            if self.nf_corr_obj is not None:
                # if so grab them
                nf_cal = self.nf_corr_obj.get_correction_vector(packet_freq,
                                                                number_of_points)
            else:
                # if no set it to 0
                nf_cal = np.zeros(number_of_points)

            # check if we have corrrection vectors (Spectrum)
            if self.sp_corr_obj is not None:
                # if so grab them
                sp_cal = self.sp_corr_obj.get_correction_vector(packet_freq,
                                                                number_of_points)
            else:
                # if not set it to 0
                sp_cal = np.zeros(number_of_points)

            # if the data is spectraly inverted, invert the vectors
            if packet.spec_inv:
                nf_cal = np.flipud(nf_cal)
                sp_cal = np.flipud(sp_cal)

            # calculate the correction threshold
            correction_thresh = (-135.0 + ((10.0 * packet_freq / 1e6)
                                           / 27000.0) + 10.0 * np.log10(rbw)
                                 + self._sweep_settings.attenuation)
            # creat the spectrum. per bin, if the ampltitude is above
            # correction threshold do pow_data - sp_cal else do pow_data -
            # nf_cal
            pow_data = np.where(pow_data < correction_thresh,
                                pow_data - nf_cal, pow_data - sp_cal)

        # check if DD mode was used in this sweep
        if self.packet_count == 1 and self._sweep_settings.dd_mode:
            # copy the data into the result array
            self._copy_data(0, self.dev_properties.FULL_BW['DD'], pow_data, self._sweep_settings.bandstart, self._sweep_settings.bandstop, self.spectral_data);

            if self._sweep_settings.beyond_dd:
                return
            else:
                return self._emit_data()


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
        srcrbw = float(src_fstop - src_fstart) / srclen
        dstrbw = float(dst_fstop - dst_fstart) / dstlen
        self.log("rbw = %f, %f, %f" % (srcrbw, dstrbw, self._sweep_settings.rbw))

        # check if packet start is before sweep start.  shouldn't happen, but check anyway
        self.log("boundary(start) = %f / %f" % (src_fstart, dst_fstart))
        if src_fstart < dst_fstart:
            self.log("foo")
            src_start_bin = int(float(dst_fstart - src_fstart) / srcrbw)
        else:
            self.log("bar")
            src_start_bin = 0

        # check if packet stop is after sweep stop.  this means we don't need the whole packet
        self.log("boundary(stop) = %f / %f" % (src_fstop, dst_fstop))
        if src_fstop > dst_fstop:
            self.log("foo")
            src_stop_bin = srclen - int(float(src_fstop - dst_fstop) / srcrbw)
        else:
            self.log("bar")
            src_stop_bin = srclen

        # how many values are we copying?
        tocopy = src_stop_bin - src_start_bin

        # calculate dest start index
        if src_fstart < dst_fstart:
            dst_start_bin = 0
        else:
            dst_start_bin = int(round(float(src_fstart - dst_fstart) / dstrbw))

        # calculate dest stop index
        dst_stop_bin = dst_start_bin + tocopy
        if dst_stop_bin > dstlen:
            dst_stop_bin = dstlen

            # adjust tocopy
            tocopy = dst_stop_bin - dst_start_bin

            # adjust src stop bin because we adjusted tocopy
            src_stop_bin = src_start_bin + tocopy

        # copy the data, if there's data that needs copying
        if ((dst_stop_bin - dst_start_bin) > 0) and ((src_stop_bin - src_start_bin) > 0):
            self.log("dst_psd[%d:%d] = src_psd[%d:%d]" % (dst_start_bin, dst_stop_bin, src_start_bin, src_stop_bin))
            dst_psd[dst_start_bin:dst_stop_bin] = src_psd[src_start_bin:src_stop_bin]
