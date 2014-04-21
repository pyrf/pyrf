from PySide import QtCore

from pyrf.sweep_device import SweepDevice
from pyrf.capture_device import CaptureDevice
from pyrf.gui import gui_config
from pyrf.numpy_util import compute_fft


class SpecAState(object):
    """
    Representation of the Spec-A + device state for passing
    to UI widgets when changed and for passing to plots when
    captures are received. This object should be treated as
    read-only.

    Parameters after 'other' may be unspecified/set to None to leave
    the value unchanged.

    :param other: existing DeviceState object to copy
    :param mode: Spec-A mode, e.g. 'ZIF' or 'SH sweep'
    :param center: center frequency in Hz
    :param rbw: RBW in Hz
    :param span: span in Hz
    :param decimation: decimation where 1 is no decimation
    :param fshift: fshift in Hz
    :param device_settings: device-specific settings dict
    :param device_class: name of device class, e.g. 'thinkrf.WSA'
    :param device_identifier: device identification string
    :param playback: set to True if this state is from a recording
    """
    def __init__(self, other=None, mode=None, center=None, rbw=None,
            span=None, decimation=None, fshift=None, device_settings=None,
            device_class=None, device_identifier=None, playback=None):

        self.mode = other.mode if mode is None else mode
        self.center = other.center if center is None else center
        self.rbw = other.rbw if rbw is None else rbw
        self.span = other.span if span is None else span
        self.decimation = (other.decimation
            if decimation is None else decimation)
        self.fshift = other.fshift if fshift is None else fshift
        self.device_settings = dict(other.device_settings
            if device_settings is None else device_settings)
        self.device_class = (other.device_class
            if device_class is None else device_class)
        self.device_identifier = (other.device_identifier
            if device_identifier is None else device_identifier)
        self.playback = other.playback if playback is None else playback

    @classmethod
    def from_json_object(cls, j, playback=True):
        """
        Create state from an unserialized JSON dict.

        :param j: dict containing values for all state parameters
            except playback
        :param playback: plaback value to use, default True
        """
        try:
            return cls(None, playback=playback, **j)
        except AttributeError:
            raise TypeError('JSON missing required settings %r' % data)

    def to_json_object(self):
        """
        Return this state as a dict that can be serialized as JSON.

        Playback state is excluded.
        """
        return {
            'mode': self.mode,
            'center': self.center,
            'rbw': self.rbw,
            'span': self.span,
            'decimation': self.decimation,
            'fshift': self.fshift,
            'device_settings': self.device_settings,
            'device_class': self.device_class,
            'device_identifier': self.device_identifier,
            # don't serialize playback info
            })


class SpecAController(QtCore.QObject):
    """
    The controller for the speca-gui.

    Issues commands to device, stores and broadcasts changes to GUI state.
    """
    _dut = None
    _sweep_device = None
    _capture_device = None
    _plot_state = None
    _speca_state = None

    device_change = QtCore.Signal(gui_config.PlotState, object)
    state_change = QtCore.Signal(gui_config.PlotState)
    capture_receive = QtCore.Signal(gui_config.PlotState, object, object, object, object)

    def set_device(self, dut):
        if self._dut:
            self._dut.disconnect()
        self._dut = dut
        self._sweep_device = SweepDevice(dut, self.process_sweep)
        self._plot_state = gui_config.PlotState(dut.properties)
        self._capture_device = CaptureDevice(dut,
            async_callback=self.process_capture,
            device_settings=self._plot_state.dev_set)

        self.device_change.emit(self._plot_state, dut)


    def read_block(self):
        self._capture_device.capture_time_domain(self._plot_state.rbw)


    def read_sweep(self):
        device_set = dict(self._plot_state.dev_set)
        device_set.pop('rfe_mode')
        device_set.pop('freq')
        device_set.pop('decimation')
        device_set.pop('fshift')
        device_set.pop('iq_output_path')
        self._sweep_device.capture_power_spectrum(
            self._plot_state.fstart,
            self._plot_state.fstop,
            self._plot_state.rbw,
            device_set,
            mode=self._sweep_mode)


    def process_capture(self, fstart, fstop, data):
        # store usable bins before next call to capture_time_domain
        usable_bins = list(self._capture_device.usable_bins)

        # only read data if WSA digitizer is used
        if self._plot_state.dev_set['iq_output_path'] == 'DIGITIZER':
            if not self._plot_state.block_mode:
                self.read_sweep()
                return
            self.read_block()
            if 'reflevel' in data['context_pkt']:
                self._ref_level = data['context_pkt']['reflevel']

            pow_data = compute_fft(self._dut,
                data['data_pkt'], data['context_pkt'], ref=self._ref_level)

            self.capture_receive.emit(
                self._plot_state,
                data['data_pkt'],
                pow_data,
                usable_bins,
                None)

    def process_sweep(self, fstart, fstop, data):
        sweep_segments = list(self._sweep_device.sweep_segments)
        if self._plot_state.block_mode:
            self.read_block()
            return
        self.read_sweep()

        if len(data) > 2:
            self.pow_data = data
        self.iq_data = None

        self.capture_receive.emit(
            self._plot_state,
            None,
            self.pow_data,
            None,
            sweep_segments)

