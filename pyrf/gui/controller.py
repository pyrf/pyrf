import logging
import ConfigParser

from PySide import QtCore
import numpy as np  # FIXME: move sweep playback out of here
from datetime import datetime
from pyrf.sweep_device import SweepDevice
from pyrf.capture_device import CaptureDevice
from pyrf.gui.gui_config import windowOptions, plotState, markerState, traceState
from pyrf.gui.state import SpecAState
from pyrf.numpy_util import compute_fft
from pyrf.vrt import vrt_packet_reader
from pyrf.devices.playback import Playback
from pyrf.util import (compute_usable_bins, adjust_usable_fstart_fstop,
    trim_to_usable_fstart_fstop, decode_config_type)

logger = logging.getLogger(__name__)

PLAYBACK_STEP_MSEC = 1

class SpecAController(QtCore.QObject):
    """
    The controller for the rtsa-gui.

    Issues commands to device, stores and broadcasts changes to GUI state.
    """
    _dut = None
    _sweep_device = None
    _capture_device = None
    _plot_options = None
    _state = None
    _recording_file = None
    _csv_file = None
    _export_csv = False
    _playback_file = None
    _playback_sweep_data = None
    _pending_user_xrange = None
    _applying_user_xrange = False
    _user_xrange_control_enabled = True
    _single_capture = False
    device_change = QtCore.Signal(object)
    state_change = QtCore.Signal(SpecAState, list)
    capture_receive = QtCore.Signal(SpecAState, float, float, object, object, object, object)
    options_change = QtCore.Signal(dict, list)
    plot_change = QtCore.Signal(dict, list)
    window_change = QtCore.Signal(dict, list)
    marker_change = QtCore.Signal(int, dict, list)
    trace_change = QtCore.Signal(int, list, list)


    def __init__(self, developer_mode = False):
        super(SpecAController, self).__init__()
        self._dsp_options = {}
        self._options = {}


        self._window_options = windowOptions
        self._plot_options = plotState
        self._marker_options = markerState
        self._trace_options = traceState
        self.developer_mode = developer_mode
        self.was_sweeping = False

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
        if not (self._plot_options['cont_cap_mode'] or self._single_capture):
            return
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
            self._state.rbw,
            force_change = self.was_sweeping)
        self.was_sweeping = False
        self._single_capture = False

    def read_sweep(self):
        if not (self._plot_options['cont_cap_mode'] or self._single_capture):
            return
        self._apply_pending_user_xrange()
        device_set = dict(self._state.device_settings)
        device_set.pop('iq_output_path')
        device_set.pop('trigger')
        self._dut.pll_reference(device_set['pll_reference'])
        device_set.pop('pll_reference')
        self._sweep_device.capture_power_spectrum(
            self._state.center - self._state.span / 2.0,
            self._state.center + self._state.span / 2.0,
            self._state.rbw,
            device_set,
            mode=self._state.rfe_mode())
        self.was_sweeping = True
        self._single_capture = False

    def start_capture(self, single = False):
        self._single_capture = single
        if self._playback_file:
            self.schedule_playback()
        elif self._state.sweeping():
            self.read_sweep()
        else:
            self.read_block()

    def schedule_playback(self):
        if self._single_capture:
            self._playback_started = False
        if not self._playback_started:
            QtCore.QTimer.singleShot(0, self._playback_step)
            self._playback_started = True

    def _playback_step(self, single = False):

        if not (self._plot_options['cont_cap_mode'] or self._single_capture):
            return
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
                self._single_capture = False
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
        elif 'mode' in changed and 'span' not in changed:
            span = self._dut.properties.DEFAULT_SPECA_SPAN
            state = SpecAState(state, span=span)
            changed.append('span')
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

       # apply trace state
        for t in self._trace_options:
            self.trace_change.emit(t, dict(self._trace_options), self._trace_options[0].keys())

        # apply marker state
        changes = self._marker_options[0].keys()
        # disable peak left/right and center
        changes.remove('peak')
        changes.remove('peak_left')
        changes.remove('peak_right')
        changes.remove('center')
        for m in self._marker_options:
            self.marker_change.emit(m, dict(self._marker_options), changes)

        # apply plot state
        self.plot_change.emit(dict(self._plot_options),
            self._plot_options.keys())

        # apply window state
        self.window_change.emit(dict(self._window_options),
            self._window_options.keys())

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


    def apply_plot_options(self, **kwargs):
        """
        Apply plot option changes and signal the change

        :param kwargs: keyword arguments of the plot options
        """
        self._plot_options.update(kwargs)
        self.plot_change.emit(dict(self._plot_options),
            kwargs.keys())
    
    def apply_marker_options(self, marker, changed, value):
        """
        Apply marker changes and signal the change
        :param marker: marker affected by change
        :param changed: a list of the changes which occurred
        :param value: a list of values corresponding to the changes
        
        """

        for i, c in enumerate(changed):

            self._marker_options[marker].update({c : value[i]})

        self.marker_change.emit(marker, dict(self._marker_options), changed)

    def apply_trace_options(self, trace, changed, value):
        """
        Apply trace changes and signal the change

        :param trace: trace affected by change
        :param changed: the change which occurred
        :param value: a list of values corresponding to the changes
        """
        for i, c in enumerate(changed):
            self._trace_options[trace].update({c : value[i]})
        self.trace_change.emit(trace, dict(self._trace_options), changed)

    def get_options(self):
        return dict(self._options)

    def apply_window_options(self, **kwargs):
        """
        Apply window options and signal the change

        :param kwargs: keyword arguments of the window options
        """
        self._window_options.update(kwargs)
        self.window_change.emit(dict(self._window_options),
            kwargs.keys())

    def enable_user_xrange_control(self, enable):
        self._user_xrange_control_enabled = enable
        if not enable:
            self._pending_user_xrange = None

    def user_xrange_changed(self, start, stop):
        if self._user_xrange_control_enabled:
            self._pending_user_xrange = start, stop

    def applying_user_xrange(self):
        return self._applying_user_xrange

    def save_settings(self, dir):
        cfgfile = open(dir,'w')
        config = ConfigParser.SafeConfigParser()
        state = self._state.to_json_object()

        config.add_section('device_options')
        for s in state:
            if 'dict' in str(type(state[s])):
                for k in state[s]:
                    if 'dict' in str(type(state[s][k])):
                        for j in state[s][k]:
                            option = j
                            value = state[s][k][j]
                            config.set('device_options', option, str(value))
                    else:
                        option = k
                        value = state[s][k]
                        config.set('device_options', option, str(value))
                continue

            else:
                option = s
                value = state[s]
            config.set('device_options', option, str(value))

        config.add_section('plot_options')
        for p in self._plot_options:
            if 'dict' in str(type(self._plot_options[p])):
                for l in self. _plot_options[p]:
                    option = l
                    value = str(self._plot_options[p][l])
                    config.set('plot_options', option, value)
                continue
            config.set('plot_options', p, str(self._plot_options[p]))

        config.add_section('options')
        for p in self._options:
            config.set('options', p, str(self._options[p]))

        config.add_section('window_options')
        for p in self._window_options:
            config.set('window_options', p, str(self._window_options[p]))

        config.add_section('marker_options')
        for p in self._marker_options:
            for s in self._marker_options[p]:
                config.set('marker_options', '%s-%s' % (str(p), s), str(self._marker_options[p][s]))
        
        config.add_section('trace_options')
        for p in self._trace_options:
            for s in self._trace_options[p]:
                config.set('trace_options', '%s-%s' % (str(p), s), str(self._trace_options[p][s]))
        config.write(cfgfile)
        cfgfile.close()

    def load_settings(self, dir):
        config = ConfigParser.SafeConfigParser()
        config.read(dir)
        plot_options = {'traces':{}}
        device_options = {'device_settings': {'trigger': {}}}
        options = {}
        window_options = {}

        state = self._state.to_json_object()

        for p in config.options('plot_options'):
            if p in self._plot_options:
                plot_options[p] = decode_config_type(config.get('plot_options', p), self._plot_options[p])

        self.plot_change.emit(dict(plot_options), plot_options.keys())

        for s in config.options('device_options'):
            if s in state:
                device_options[s] = decode_config_type(config.get('device_options', s), state[s])
            elif s in state['device_settings']:
                device_options['device_settings'][s] = decode_config_type(config.get('device_options', s), state['device_settings'][s])
            elif s in state['device_settings']['trigger']:
                device_options['device_settings']['trigger'][s] = decode_config_type(config.get('device_options', s), state['device_settings']['trigger'][s])

        for p in config.options('options'):
            options[p] = decode_config_type(config.get('options', p), self._options[p])

        for p in config.options('window_options'):
            window_options[p] = decode_config_type(config.get('window_options', p), self._window_options[p])

        for p in config.options('marker_options'):
            name = int(p.split('-')[0])
            property = p.split('-')[1]
            self._marker_options[name][property] = decode_config_type(config.get('marker_options', p), self._marker_options[name][property])
        for p in config.options('trace_options'):
            name = int(p.split('-')[0])
            property = p.split('-')[1]
            self._trace_options[name][property] = decode_config_type(config.get('trace_options', p), self._trace_options[name][property])

        state = SpecAState(self._state, **device_options)
        self._apply_complete_settings(device_options, False)
        self.apply_options(**options)
        self.apply_window_options(**window_options)
        
        # add config to inform plot options that a config has been laoded
        plot_options['config'] = True
        self.apply_plot_options(**plot_options)
