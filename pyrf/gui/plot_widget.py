import platform

import pyqtgraph as pg
import numpy as np
from PySide import QtCore

from pyrf.gui import colors
from pyrf.gui import labels
from pyrf.gui import fonts
from pyrf.gui.widgets import SpectralWidget
from pyrf.gui.amplitude_controls import PLOT_TOP, PLOT_BOTTOM
from pyrf.gui.waterfall_widget import (WaterfallModel,
                                       ThreadedWaterfallPlotWidget)
from pyrf.gui.persistence_plot_widget import (PersistencePlotWidget,
                                              decay_fn_EXPONENTIAL)
from pyrf.gui.plot_tools import Marker, Trace, InfiniteLine, triggerControl
from pyrf.units import M
from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)

PLOT_YMIN = -5000
PLOT_YMAX = 5000

IQ_PLOT_YMIN = -1
IQ_PLOT_YMAX = 1

IQ_PLOT_XMIN = -1
IQ_PLOT_XMAX = 1

# FIXME: we shouldn't be calculating fft in this module
ZIF_BITS = 2**13
CONST_POINTS = 512

PERSISTENCE_RESETTING_CHANGES = set(["center",
                                     "device_settings.attenuator",
                                     #"rbw",  <-- signal is the same area
                                     "mode"
                                     ])

class Plot(QtCore.QObject):
    """
    Class to hold plot widget, as well as all the plot items (curves, marker_arrows,etc)
    """
    user_xrange_change = QtCore.Signal(float, float)

    def __init__(self, controller, layout):
        super(Plot, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)
        controller.plot_change.connect(self.plot_changed)
        self.plot_state = {}

        # initialize main fft window
        self.spectral_window = SpectralWidget(controller)
        self.window = self.spectral_window.window

        self.window.setMenuEnabled(False)

        def widget_range_changed(widget, ranges):
            if hasattr(self, 'gui_state') and hasattr(self, 'plot_state'):
                # HDR mode has a tuning resolution almost the same as its usable bandwidth, making the tuning mouse tuning annoying to use
                if self.gui_state.mode == 'HDR' or not self.plot_state['mouse_tune']:
                    return
            if not hasattr(ranges, '__getitem__'):
                return  # we're not intereted in QRectF updates
            self.user_xrange_change.emit(ranges[0][0], ranges[0][1])

        self.window.sigRangeChanged.connect(widget_range_changed)

        self.view_box = self.window.plotItem.getViewBox()

        # initialize the y-axis of the plot
        self.window.setYRange(PLOT_BOTTOM, PLOT_TOP)
        labelStyle = fonts.AXIS_LABEL_FONT

        self.window.setLabel('left', 'Power', 'dBm', **labelStyle)
        self.window.setLabel('top')
        self.window.setLabel('bottom', 'Frequency', 'Hz', **labelStyle)

        # horizontal cursor line
        cursor_pen = pg.mkPen(color = colors.YELLOW_NUM, width = 2)
        self.cursor_line = pg.InfiniteLine(pos = -100, angle = 0, movable = True, pen = cursor_pen)

        self.channel_power_region = pg.LinearRegionItem()
        self._trig_enable = False
        self.grid(True)

        # IQ constellation window
        self.const_window = pg.PlotWidget(name='const_plot')
        self.const_plot = pg.ScatterPlotItem(pen = 'y')
        self.const_window.setMenuEnabled(False)
        self.const_window.addItem(self.const_plot)
        self.const_window.setYRange(IQ_PLOT_YMIN, IQ_PLOT_YMAX)
        self.const_window.setXRange(IQ_PLOT_YMIN, IQ_PLOT_YMAX)  

        # IQ time domain  window
        self.iq_window = pg.PlotWidget(name='const_plot')
        self.iq_window.setYRange(IQ_PLOT_YMIN, IQ_PLOT_YMAX)
        self.iq_window.setMenuEnabled(False)
        self.update_iq_range = True
        self.i_curve = self.iq_window.plot(pen = 'g')
        self.q_curve = self.iq_window.plot(pen = 'r')

        # add traces
        self.traces = []
        first_trace = labels.TRACES[0]

        for trace_name, trace_color in zip(labels.TRACES, colors.TRACE_COLORS):
            trace = Trace(
                self,
                trace_name,
                trace_color,
                blank=True,
                write=False)
            self.traces.append(trace)
        self.traces[0].blank = False
        self.traces[0].write = True

        self.markers = []
        for name in labels.MARKERS:
            self.markers.append(Marker(self, name, colors.WHITE_NUM, self.controller))

        self.waterfall_data = WaterfallModel(max_len=600)

        self.waterfall_window = ThreadedWaterfallPlotWidget(
            self.waterfall_data,
            scale_limits=(PLOT_YMIN, PLOT_YMAX),
            max_frame_rate_fps=30,
            mouse_move_crosshair=False,
            )
        self.persistence_window = PersistencePlotWidget(
            decay_fn=decay_fn_EXPONENTIAL,
            data_model=self.waterfall_data)
        self.persistence_window.getAxis('bottom').setScale(1e-9)
        self.persistence_window.showGrid(True, True)


        self.trigger_control = triggerControl()
        self.connect_plot_controls()
        self.update_waterfall_levels(PLOT_BOTTOM, PLOT_TOP)
    def connect_plot_controls(self):
        def new_channel_power():
            self.controller.apply_plot_options(channel_power_region = self.channel_power_region.getRegion())
        def new_cursor_value():
            self.controller.apply_plot_options(horizontal_cursor_value = self.cursor_line.value())

        def new_trigger():
            self.controller.apply_device_settings(trigger = {'type': 'LEVEL',
                                                        'fstart':self.trigger_control.fstart,
                                                        'fstop': self.trigger_control.fstop,
                                                        'amplitude': self.trigger_control.amplitude})
        def new_y_axis():
            self.controller.apply_plot_options(y_axis = self.view_box.viewRange()[1])
        # update trigger settings when ever a line is changed
        self.channel_power_region.sigRegionChanged.connect(new_channel_power)
        self.cursor_line.sigPositionChangeFinished.connect(new_cursor_value)
        self.trigger_control.sigNewTriggerRange.connect(new_trigger)
        self.window.sigYRangeChanged.connect(new_y_axis)
    def device_changed(self, dut):
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state
        if 'device_settings.trigger' in changed:
            fstart = state.device_settings['trigger']['fstart']
            fstop = state.device_settings['trigger']['fstop']
            amplitude = state.device_settings['trigger']['amplitude']
            type = state.device_settings['trigger']['type']

            if type == 'NONE':
                self.remove_trigger()
                self.trigger_control.resize_trigger(fstart, fstop, amplitude)
            elif type == 'LEVEL':
                self.add_trigger(fstart,
                                fstop,
                                amplitude)
                for m in self.markers:
                    if m.enabled:
                        m.remove_marker(self)
                        m.add_marker(self)

        if 'center' in changed or 'span' in changed:
            fstart = state.center - (state.span / 2)
            fstop = state.center + (state.span / 2)
            for trace in self.traces:
                trace.clear_data()

            if fstart > self.trigger_control.fstart or fstop < self.trigger_control.fstop:
                self.controller.apply_device_settings(trigger = {'type': 'NONE',
                                                        'fstart':self.trigger_control.fstart,
                                                        'fstop': self.trigger_control.fstop,
                                                        'amplitude': self.trigger_control.amplitude})
                self.remove_trigger()
                self.persistence_window.reset_plot()
            if fstart > float(min(self.channel_power_region.getRegion())) or fstop < float(max(self.channel_power_region.getRegion())):
                self.move_channel_power(fstart + state.span / 4, fstop - state.span / 4)

        if set(changed).intersection(PERSISTENCE_RESETTING_CHANGES):
            self.persistence_window.reset_plot()

        if 'mode' in changed:
            if state.mode not in self.dut_prop.LEVEL_TRIGGER_RFE_MODES:
                self.remove_trigger()

    def plot_changed(self, state, changed):

        self.plot_state = state
        if 'horizontal_cursor' in changed:
            if state['horizontal_cursor']:
                self.window.addItem(self.cursor_line)
            else:
                self.window.removeItem(self.cursor_line)
        if 'channel_power' in changed:
            if state['channel_power']:
                self.enable_channel_power()
            else:
                self.disable_channel_power()
        if 'horizontal_cursor_value' in changed:
            self.cursor_line.setValue(state['horizontal_cursor_value'])
        if 'channel_power_region' in changed:
            for t in self.traces:
                t.channel_power_range = state['channel_power_region']
                t.compute_channel_power()
        if 'y_axis' in changed:
            self.window.setYRange(state['y_axis'][0] , state['y_axis'][1], padding = 0)
            self.persistence_window.setYRange(state['y_axis'][0] , state['y_axis'][1], padding = 0)

    def enable_channel_power(self):
        for t in self.traces:
            t.calc_channel_power = True
        fstart = self.gui_state.center - (self.gui_state.span / 4)
        fstop = self.gui_state.center + (self.gui_state.span / 4)
        self.move_channel_power(fstart, fstop)
        self.window.addItem(self.channel_power_region)

    def move_channel_power(self, fstart, fstop):
        self.channel_power_region.setRegion([(fstart),float(fstop)])

    def disable_channel_power(self):
        for t in self.traces:
            t.calc_channel_power = False
        self.window.removeItem(self.channel_power_region)

    def add_trigger(self,fstart, fstop, amplitude):

        if not self._trig_enable:
            self.window.addItem(self.trigger_control)
            self.window.addItem(self.trigger_control.fstart_line)
            self.window.addItem(self.trigger_control.fstop_line)
            self.window.addItem(self.trigger_control.amplitude_line)
            self._trig_enable = True
        self.trigger_control.resize_trigger(fstart,
                                             fstop,
                                             amplitude)

    def remove_trigger(self):
        self.window.removeItem(self.trigger_control)
        self.window.removeItem(self.trigger_control.fstart_line)
        self.window.removeItem(self.trigger_control.fstop_line)
        self.window.removeItem(self.trigger_control.amplitude_line)
        self._trig_enable = False

    def center_view(self, fstart, fstop):
        b = self.window.blockSignals(True)
        self.window.setXRange(float(fstart), float(fstop), padding=0)
        self.window.blockSignals(b)
        self.persistence_window.setXRange(
            float(fstart),
            float(fstop),
            padding=0)

    def update_waterfall_levels(self, min_level, ref_level):
        if self.waterfall_window is not None:
            self.waterfall_window.set_lookup_levels(min_level, ref_level)
        self.persistence_window.reset_plot()
        self.persistence_window.setYRange(min_level, ref_level)

    def grid(self,state):
        self.window.showGrid(state,state)
        self.window.getAxis('bottom').setPen(colors.GREY_NUM)
        self.window.getAxis('bottom').setGrid(200)
        self.window.getAxis('left').setPen(colors.GREY_NUM)
        self.window.getAxis('left').setGrid(200)
        self.window.getAxis('top').setTicks([[(-200, '-200'), (-200, '-200'),
                                            (-250, '-200'), (-250, '-200')]])
    def update_markers(self):
        for m in self.markers:
            if m.enabled:
                trace = self.traces[m.trace_index]
                m.update_pos(trace.freq_range, trace.data)

    def get_trigger_region(self):
        print self.trigger_control.pos()
        print self.trigger_control.size()

    def update_iq_plots(self, data):
        
        trace = self.traces[0]
        if not (trace.write or trace.max_hold or trace.min_hold or trace.store):
            return

        if data.stream_id == VRT_IFDATA_I14Q14:
            i_data = np.array(data.data.numpy_array()[:,0], dtype=float)/ZIF_BITS
            q_data = np.array(data.data.numpy_array()[:,1], dtype=float)/ZIF_BITS

            self.i_curve.setData(i_data)
            self.q_curve.setData(q_data)
            self.const_plot.clear()
            self.const_plot.addPoints(
                x = i_data[0:CONST_POINTS],
                y = q_data[0:CONST_POINTS],
                symbol = 'o',
                size = 1, pen = 'y',
                brush = 'y')
        else:
            i_data = np.array(data.data.numpy_array(), dtype=float)
            if data.stream_id == VRT_IFDATA_I14:
                i_data = i_data /ZIF_BITS

            elif data.stream_id == VRT_IFDATA_I24:
                i_data = i_data / (np.mean(i_data)) - 1

            self.i_curve.setData(i_data)
            self.q_curve.clear()

        if self.update_iq_range:
            self.iq_window.setXRange(0, len(i_data))
            self.update_iq_range = False

    def center_iq_plots(self):
        self.iq_window.setYRange(IQ_PLOT_YMIN, IQ_PLOT_YMAX)

