
from PySide import QtCore

from pyrf.sweep_device import SweepDevice
from pyrf.capture_device import CaptureDevice
from pyrf.gui import gui_config
from pyrf.numpy_util import compute_fft


class SpecAController(QtCore.QObject):
    """
    The controller for the speca-gui.

    Issues commands to device, stores and broadcasts changes to GUI state.
    """
    _dut = None
    _sweep_device = None
    _capture_device = None
    _plot_state = None

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

