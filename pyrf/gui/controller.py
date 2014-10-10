import logging

from PySide import QtCore
import numpy as np  # FIXME: move sweep playback out of here
from datetime import datetime
from pyrf.sweep_device import SweepDevice
from pyrf.capture_device import CaptureDevice
from pyrf.gui import gui_config
from pyrf.gui.state import SpecAState
from pyrf.numpy_util import compute_fft
from pyrf.vrt import vrt_packet_reader
from pyrf.devices.playback import Playback
from pyrf.util import (compute_usable_bins, adjust_usable_fstart_fstop,
    trim_to_usable_fstart_fstop)

logger = logging.getLogger(__name__)

PLAYBACK_STEP_MSEC = 100

class SpecAController(QtCore.QObject):
    """
    The controller for the rtsa-gui.

    Issues commands to device, stores and broadcasts changes to GUI state.
    """
    _dut = None
    _sweep_device = None
    _capture_device = None
    _plot_state = None
    _state = None
    _recording_file = None
    _csv_file = None
    _export_csv = False
    _playback_file = None
    _playback_sweep_data = None
    _user_xrange_control_enabled = True
    _pending_user_xrange = None
    _applying_user_xrange = False

    device_change = QtCore.Signal(object)
    state_change = QtCore.Signal(SpecAState, list)
    capture_receive = QtCore.Signal(SpecAState, float, float, object, object, object, object)
    options_change = QtCore.Signal(dict, list)
    plot_change = QtCore.Signal(dict, list)
    def __init__(self, developer_mode = False):
        super(SpecAController, self).__init__()
        self._dsp_options = {}
        self._options = {}
        self._plot_options = {}
        self.developer_mode = developer_mode


    def set_device(self, dut=None, playback_filename=None):
        """
        Detach any currenly attached device and stop playback then
        optionally attach to a new device or playback file.

        :param dut: a :class:`pyrf.thinkrf.WSA` or None
        :param playback_filename: recorded VRT data filename or None
        :param playback_scheduler: function to schedule each playback capture
        """
        if self._playback_file:
            self._playback_file.close()
            self._playback_file = None

        if self._dut:
            self._dut.disconnect()

        if playback_filename:
            self._playback_file = open(playback_filename, 'rb')
            self._playback_started = False
            self._playback_context = {}
            vrt_packet = self._playback_vrt(auto_rewind=False)
            state_json = vrt_packet.fields['speca']
            # support old playback files
            if state_json['device_identifier'] == 'unknown':
                state_json['device_identifier'] = 'ThinkRF,WSA5000 v3,0,0'
            dut = Playback(state_json['device_class'],
                state_json['device_identifier'])
            self._sweep_device = SweepDevice(dut)
            self._capture_device = CaptureDevice(dut)
        elif dut:
            dut.reset()
            self._sweep_device = SweepDevice(dut, self.process_sweep)
            self._capture_device = CaptureDevice(dut, self.process_capture)
            state_json = dict(
                dut.properties.SPECA_DEFAULTS,
                device_identifier=dut.device_id)

        self._dut = dut
        if not dut:
            return

        self.device_change.emit(dut)
        self._apply_complete_settings(state_json, bool(self._playback_file))
        self.start_capture()

    def start_recording(self, filename):
        """
        Start a new recording. Does nothing if we're
        currently playing a recording.
        """
        if self._playback_file:
            return
        self.stop_recording()
        self._recording_file = open(filename, 'wb')
        self._dut.set_recording_output(self._recording_file)
        self._dut.inject_recording_state(self._state.to_json_object())

    def stop_recording(self):
        """
        Stop recording or do nothing if not currently recording.
        """
        if not self._recording_file:
            return
        self._dut.set_recording_output(None)
        self._recording_file.close()
        self._recording_file = None

    def start_csv_export(self, filename):
        """
        Start exporting datainto CSV file
        """
        self._csv_file = open(filename, 'wb')
        self._csv_file.write('data,mode,fstart,fstop,size,timestamp\n')
        self._export_csv = True

    def stop_csv_export(self):
        """
        Stop exporting data into  CSV file
        """
        self._csv_file.close()
        self._export_csv = False

    def _export_csv_file(self, mode, fstart, fstop, data):
        """
        Save data to csv file
        """
        time = datetime.isoformat(datetime.utcnow()) + 'Z'
        self._csv_file.write(',%s,%0.2f,%0.2f,%d,%s\n' % (mode, fstart, fstop, len(data), time))
        for d in data:
            self._csv_file.write('%0.2f\n' % d)

    def _apply_pending_user_xrange(self):
        if self._pending_user_xrange:
            self._applying_user_xrange = True
            start, stop = self._pending_user_xrange
            self._pending_user_xrange = None
            self.apply_settings(
                center=int((start + stop) / 2.0
                    / self._dut.properties.TUNING_RESOLUTION)
                    * self._dut.properties.TUNING_RESOLUTION,
                span=stop - start)
        else:
            self._applying_user_xrange = False

    def read_block(self):
        self._apply_pending_user_xrange()
        device_set = dict(self._state.device_settings)
        device_set['decimation'] = self._state.decimation
        device_set['fshift'] = self._state.fshift
        device_set['rfe_mode'] = self._state.rfe_mode()
        device_set['freq'] = self._state.center
        self._capture_device.configure_device(device_set)

        self._capture_device.capture_time_domain(
            self._state.mode,
            self._state.center,
            self._state.rbw)

    def read_sweep(self):
        self._apply_pending_user_xrange()
        device_set = dict(self._state.device_settings)
        device_set.pop('pll_reference')
        device_set.pop('iq_output_path')
        device_set.pop('trigger')

        self._sweep_device.capture_power_spectrum(
            self._state.center - self._state.span / 2.0,
            self._state.center + self._state.span / 2.0,
            self._state.rbw,
            device_set,
            mode=self._state.rfe_mode())

    def start_capture(self):
        if self._playback_file:
            self.schedule_playback()
        elif self._state.sweeping():
            self.read_sweep()
        else:
            self.read_block()

    def schedule_playback(self):
        if not self._playback_started:
            QtCore.QTimer.singleShot(0, self._playback_step)
            self._playback_started = True

    def _playback_step(self):
        if not self._playback_file:
            self._playback_started = False
            return

        QtCore.QTimer.singleShot(PLAYBACK_STEP_MSEC, self._playback_step)

        while True:
            pkt = self._playback_vrt()

            if pkt.is_context_packet():
                if 'speca' in pkt.fields:
                    self._playback_sweep_data = None
                    state_json = pkt.fields['speca']
                    self._apply_complete_settings(state_json, playback=True)
                else:
                    self._playback_context.update(pkt.fields)
                continue

            if self._state.sweeping():
                if not self._playback_sweep_step(pkt):
                    continue
                return
            break

        usable_bins = compute_usable_bins(
            self._dut.properties,
            self._state.rfe_mode(),
            len(pkt.data),
            self._state.decimation,
            self._state.fshift)

        usable_bins, fstart, fstop = adjust_usable_fstart_fstop(
            self._dut.properties,
            self._state.rfe_mode(),
            len(pkt.data),
            self._state.decimation,
            self._state.center,
            pkt.spec_inv,
            usable_bins)

        pow_data = compute_fft(
            self._dut,
            pkt,
            self._playback_context,
            **self._dsp_options)

        if not self._options.get('show_attenuated_edges'):
            pow_data, usable_bins, fstart, fstop = (
                trim_to_usable_fstart_fstop(
                    pow_data, usable_bins, fstart, fstop))
        if self._export_csv:
            self._export_csv_file(self._state.rfe_mode(), fstart, fstop, pow_data)
        self.capture_receive.emit(
            self._state,
            fstart,
            fstop,
            pkt,
            pow_data,
            usable_bins,
            None)

    def _playback_sweep_start(self):
        """
        ready a new playback sweep data array
        """
        nans = np.ones(int(self._state.span / self._state.rbw)) * np.nan
        self._playback_sweep_data = nans

    def _playback_sweep_step(self, pkt):
        """
        process one data packet from a recorded sweep and
        plot collected data after receiving complete sweep.

        returns True if data was plotted on this step.
        """
        if self._playback_sweep_data is None:
            self._playback_sweep_start()
            last_center = None
        else:
            last_center = self._playback_sweep_last_center

        sweep_start = float(self._state.center - self._state.span / 2)
        sweep_stop = float(self._state.center + self._state.span / 2)
        step_center = self._playback_context['rffreq']
        updated_plot = False
        if last_center is not None and last_center >= step_center:
            # starting a new sweep, plot the data we have
            self.capture_receive.emit(
                self._state,
                sweep_start,
                sweep_stop,
                None,
                self._playback_sweep_data,
                None,
                None)
            updated_plot = True
            self._playback_sweep_start()
        self._playback_sweep_last_center = step_center

        usable_bins = compute_usable_bins(
            self._dut.properties,
            self._state.rfe_mode(),
            len(pkt.data),
            self._state.decimation,
            self._state.fshift)

        usable_bins, fstart, fstop = adjust_usable_fstart_fstop(
            self._dut.properties,
            self._state.rfe_mode(),
            len(pkt.data),
            self._state.decimation,
            step_center,
            pkt.spec_inv,
            usable_bins)

        pow_data = compute_fft(
            self._dut,
            pkt,
            self._playback_context,
            **self._dsp_options)

        pow_data, usable_bins, fstart, fstop = (
            trim_to_usable_fstart_fstop(
                pow_data, usable_bins, fstart, fstop))

        clip_left = max(sweep_start, fstart)
        clip_right = min(sweep_stop, fstop)
        sweep_points = len(self._playback_sweep_data)
        point_left = int((clip_left - sweep_start) * sweep_points / (
            sweep_stop - sweep_start))
        point_right = int((clip_right - sweep_start) * sweep_points / (
            sweep_stop - sweep_start))
        xvalues = np.linspace(clip_left, clip_right, point_right - point_left)

        if point_left >= point_right:
            logger.info('received sweep step outside sweep: %r, %r' %
                ((fstart, fstop), (sweep_start, sweep_stop)))
        else:
            self._playback_sweep_data[point_left:point_right] = np.interp(
                xvalues, np.linspace(fstart, fstop, len(pow_data)), pow_data)

        return updated_plot


    def _playback_vrt(self, auto_rewind=True):
        """
        Return the next VRT packet in the playback file
        """
        reader = vrt_packet_reader(self._playback_file.read)
        data = None
        try:
            while True:
                data = reader.send(data)
        except StopIteration:
            pass
        except ValueError:
            return None

        if data == '' and auto_rewind:
            self._playback_file.seek(0)
            data = self._playback_vrt(auto_rewind=False)

        return None if data == '' else data


    def process_capture(self, fstart, fstop, data):
        # store usable bins before next call to capture_time_domain
        usable_bins = list(self._capture_device.usable_bins)

        # only read data if WSA digitizer is used
        if 'DIGITIZER' in self._state.device_settings['iq_output_path']:
            if self._state.sweeping():
                self.read_sweep()
                return
            self.read_block()
            if 'reflevel' in data['context_pkt']:
                self._ref_level = data['context_pkt']['reflevel']

            pow_data = compute_fft(
                self._dut,
                data['data_pkt'],
                data['context_pkt'],
                ref=self._ref_level,
                **self._dsp_options)

            if not self._options.get('show_attenuated_edges'):
                pow_data, usable_bins, fstart, fstop = (
                    trim_to_usable_fstart_fstop(
                        pow_data, usable_bins, fstart, fstop))
            #FIXME: Find out why there is a case where pow_data may be empty
            if pow_data.any():
                if self._plot_options.get('reference_offset_value'):
                    pow_data += self._plot_options['reference_offset_value']
                if self._export_csv:
                    self._export_csv_file(self._state.rfe_mode(), fstart, fstop, pow_data)
                self.capture_receive.emit(
                    self._state,
                    fstart,
                    fstop,
                    data['data_pkt'],
                    pow_data,
                    usable_bins,
                    None)

    def process_sweep(self, fstart, fstop, data):
        sweep_segments = list(self._sweep_device.sweep_segments)
        if not self._state.sweeping():
            self.read_block()
            return
        self.read_sweep()

        if len(data) > 2:
            self.pow_data = data
        self.iq_data = None

        if not self._options.get('show_sweep_steps'):
            sweep_segments = None
        if self._plot_options.get('reference_offset_value'):
            self.pow_data += self._plot_options['reference_offset_value']
        if self._export_csv:
            self._export_csv_file(self._state.rfe_mode(), fstart, fstop, self.pow_data)
        self.capture_receive.emit(
            self._state,
            fstart,
            fstop,
            None,
            self.pow_data,
            None,
            sweep_segments)

    def _state_changed(self, state, changed):
        """
        Emit signal and handle special cases where extra work is needed in
        response to a state change.
        """
        # make sure resolution of center are the same as the device's tunning resolution
        center = float(np.round(state.center, -1 * int(np.log10(self._dut.properties.TUNING_RESOLUTION))))
        state = SpecAState(state, center=center)

        if not state.sweeping():
            # force span to correct value for the mode given
            if state.decimation > 1:
                span = (float(self._dut.properties.FULL_BW[state.rfe_mode()])
                    / state.decimation * self._dut.properties.DECIMATED_USABLE)
            else:
                span = self._dut.properties.USABLE_BW[state.rfe_mode()]
            state = SpecAState(state, span=span)
            changed = [x for x in changed if x != 'span']
            if not self._state or span != self._state.span:
                changed.append('span')

        if 'mode' in changed:
            # check if RBW is appropriate for given mode
            if state.rbw not in self._dut.properties.RBW_VALUES[state.rfe_mode()]:
                if state.sweeping():
                    rbw = self._dut.properties.RBW_VALUES[state.rfe_mode()][0]
                    state = SpecAState(state, rbw=rbw)
                else:
                    rbw = self._dut.properties.RBW_VALUES[state.rfe_mode()][-1]
                    state = SpecAState(state, rbw=rbw)
        self._state = state

        # start capture loop again when user switches output path
        # back to the internal digitizer XXX: very WSA5000-specific
        if 'device_settings.iq_output_path' in changed:
            if state.device_settings.get('iq_output_path') == 'DIGITIZER':
                self.start_capture()
            elif state.device_settings.get('iq_output_path') == 'CONNECTOR':
                if state.sweeping():
                    state.mode = self._dut.properties.RFE_MODES[0]

        if self._recording_file:
            self._dut.inject_recording_state(state.to_json_object())

        self.state_change.emit(state, changed)

    def apply_device_settings(self, **kwargs):
        """
        Apply device-specific settings and trigger a state change event.
        :param kwargs: keyword arguments of SpecAState.device_settings
        """
        device_settings = dict(self._state.device_settings, **kwargs)
        state = SpecAState(self._state, device_settings=device_settings)

        if device_settings.get('iq_output_path') == 'CONNECTOR' or 'trigger' in kwargs:
            self._capture_device.configure_device(device_settings)

        changed = ['device_settings.%s' % s for s in kwargs]
        self._state_changed(state, changed)

    def apply_settings(self, **kwargs):
        """
        Apply state settings and trigger a state change event.

        :param kwargs: keyword arguments of SpecAState attributes
        """
        if self._state is None:
            logger.warn('apply_settings with _state == None: %r' % kwargs)
            return

        state = SpecAState(self._state, **kwargs)
        self._state_changed(state, kwargs.keys())

    def _apply_complete_settings(self, state_json, playback):
        """
        Apply state setting changes from a complete JSON object. Used for
        initial settings and applying settings from a recording.
        """
        if self._state:
            old = self._state.to_json_object()
            old['playback'] = self._state.playback
        else:
            old = {}

        changed = [
            key for key, value in state_json.iteritems()
            if old.get(key) != value
            ]
        if old.get('playback') != playback:
            changed.append('playback')

        if 'device_settings' in changed:
            changed.remove('device_settings')
            oset = old.get('device_settings', {})
            dset = state_json['device_settings']
            changed.extend([
                'device_settings.%s' % key for key, value in dset.iteritems()
                if oset.get(key) != value])

        state = SpecAState.from_json_object(state_json, playback)
        self._state_changed(state, changed)

    def apply_options(self, **kwargs):
        """
        Apply menu options and signal the change

        :param kwargs: keyword arguments of the dsp options
        """
        self._options.update(kwargs)
        self.options_change.emit(dict(self._options),
            kwargs.keys())

        for key, value in kwargs.iteritems():
            if key.startswith('dsp.'):
                self._dsp_options[key[4:]] = value

        if 'free_plot_adjustment' in kwargs:
            self.enable_user_xrange_control(
                not kwargs['free_plot_adjustment'])

    def apply_plot_options(self, **kwargs):
        """
        Apply plot option changes and signal the change

        :param kwargs: keyword arguments of the plot options
        """
        self._plot_options.update(kwargs)
        self.plot_change.emit(dict(self._plot_options),
            kwargs.keys())

    def get_options(self):
        return dict(self._options)

    def enable_user_xrange_control(self, enable):
        self._user_xrange_control_enabled = enable
        if not enable:
            self._pending_user_xrange = None

    def user_xrange_changed(self, start, stop):
        if self._user_xrange_control_enabled:
            self._pending_user_xrange = start, stop

    def applying_user_xrange(self):
        return self._applying_user_xrange
