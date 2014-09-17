import platform

import pyqtgraph as pg
import numpy as np
from PySide import QtCore

from pyrf.gui import colors
from pyrf.gui import labels
from pyrf.gui import fonts
from pyrf.gui.amplitude_controls import PLOT_TOP, PLOT_BOTTOM
from pyrf.gui.waterfall_widget import (WaterfallModel,
                                       ThreadedWaterfallPlotWidget)
from pyrf.gui.persistence_plot_widget import (PersistencePlotWidget,
                                              decay_fn_EXPONENTIAL)
from pyrf.gui.widgets import infiniteLine
from pyrf.gui.freq_axis_widget import RTSAFrequencyAxisItem
from pyrf.units import M
from pyrf.vrt import (I_ONLY, VRT_IFDATA_I14Q14, VRT_IFDATA_I14,
    VRT_IFDATA_I24, VRT_IFDATA_PSD8)

PLOT_YMIN = -160
PLOT_YMAX = 20

IQ_PLOT_YMIN = -1
IQ_PLOT_YMAX = 1

IQ_PLOT_XMIN = -1
IQ_PLOT_XMAX = 1

AXIS_OFFSET = 7

# FIXME: we shouldn't be calculating fft in this module
ZIF_BITS = 2**13
CONST_POINTS = 512

PERSISTENCE_RESETTING_CHANGES = set(["center",
                                     "device_settings.attenuator",
                                     #"rbw",  <-- signal is the same area
                                     "mode"
                                     ])
class Trace(object):
    """
    Class to represent a trace in the plot
    """
    
    def __init__(self,plot_area, trace_name, trace_color, blank = False, write = False):
        self.name = trace_name
        self.max_hold = False
        self.min_hold = False
        self.blank = blank
        self.write = write
        self.store = False
        self.average = False
        self.data = None
        self.raw_packet = None
        self.freq_range = None
        self.color = trace_color
        self.edge_color = trace_color + (40,)
        self.alternate_color = (
            max(0, trace_color[0] - 60),
            max(0, trace_color[1] - 60),
            min(255, trace_color[2] + 60),)
        self.curves = []
        self.plot_area = plot_area
        self.average_list = []
        self.average_factor = 5
    def clear(self):
        for c in self.curves:
            self.plot_area.window.removeItem(c)
        self.curves = []
    def clear_data(self):
        self.average_list = []
        self.data = None
    def update_average_factor(self, factor):
        self.average_factor = factor
        self.average_list = []

    def update_curve(self, xdata, ydata, usable_bins, sweep_segments):

        if self.store or self.blank:
            return

        self.freq_range = xdata

        if self.max_hold:
            if (self.data == None or len(self.data) != len(ydata)):
                self.data = ydata
            self.data = np.maximum(self.data,ydata)

        elif self.min_hold:
            if (self.data == None or len(self.data) != len(ydata)):
                self.data = ydata
            self.data = np.minimum(self.data,ydata)

        elif self.write:
            self.data = ydata

        elif self.average:
            if len(self.average_list) >= self.average_factor:
                self.average_list.pop(0)
            if self.average_list:
                if len(ydata) != len(self.data):
                    self.average_list = []
            self.average_list.append(ydata)
            self.data = np.average(self.average_list, axis = 0)

        self.clear()
        if usable_bins:
            # plot usable and unusable curves
            i = 0
            for start_bin, run_length in usable_bins:
                if start_bin > i:
                    c = self.plot_area.window.plot(x=xdata[i:start_bin+1],
                        y=self.data[i:start_bin+1], pen=self.edge_color)
                    self.curves.append(c)
                    i = start_bin
                if run_length:
                    c = self.plot_area.window.plot(x=xdata[i:i+run_length],
                        y=self.data[i:i+run_length], pen=self.color)
                    self.curves.append(c)
                    i = i + run_length - 1
            if i < len(xdata):
                c = self.plot_area.window.plot(x=xdata[i:], y=self.data[i:],
                    pen=self.edge_color)
                self.curves.append(c)
        else:
            odd = True
            i = 0
            if sweep_segments is None:
                sweep_segments = [len(self.data)]
            for run in sweep_segments:
                c = self.plot_area.window.plot(x=xdata[i:i + run],
                    y=self.data[i:i + run],
                    pen=self.color if odd else self.alternate_color)
                self.curves.append(c)
                i = i + run
                odd = not odd

class Marker(object):
    """
    Class to represent a marker on the plot
    """
    def __init__(self,plot_area, marker_name, color):

        self.name = marker_name
        self.marker_plot = pg.ScatterPlotItem()
        self.enabled = False
        self.selected = False
        self.data_index = None
        self.xdata = []
        self.ydata = 0
        self.trace_index = 0
        self.color = color
        self.draw_color = color
        self.hovering = False
        self._plot = plot_area
        self.coursor_dragged = False

        cursor_pen = pg.mkPen((0,0,0,0), width = 40)
        self.cursor_line = infiniteLine(pen = cursor_pen, pos = -100, angle = 90, movable = True)
        self.cursor_line.setHoverPen(pg.mkPen((0,0,0, 0), width = 40))

        def dragged():
            self.data_index = np.abs( self.xdata-self.cursor_line.value()).argmin()
            self.cursor_line.setPen(cursor_pen)
            self.draw_color = colors.MARKER_HOVER
        self.cursor_line.sigDragged.connect(dragged)

        def hovering():
            self.draw_color = colors.MARKER_HOVER
        self.cursor_line.sigHovering.connect(hovering)

        def not_hovering():
            self.draw_color = color
        self.cursor_line.sigHoveringFinished.connect(not_hovering)

    def remove_marker(self, plot):
        plot.window.removeItem(self.marker_plot)
        plot.window.removeItem(self.cursor_line)

    def add_marker(self, plot):
        plot.window.addItem(self.marker_plot)
        plot.window.addItem(self.cursor_line)

    def enable(self, plot):
        self.enabled = True
        self.add_marker(plot)

    def disable(self, plot):
        self.enabled = False
        self.remove_marker(plot)
        self.data_index = None
        self.trace_index = 0

    def update_pos(self, xdata, ydata):

        self.marker_plot.clear()
        if len(xdata) <= 0 or len(ydata) <= 0:
            return

        if self.data_index  == None:
           self.data_index = len(ydata) / 2 

        if not len(xdata) == len(self.xdata) and not len(self.xdata) == 0:
            self.data_index = int((float(self.data_index)/float(len(self.xdata))) * len(xdata)) 

        xpos = xdata[self.data_index]
        ypos = ydata[self.data_index]

        self.xdata = xdata
        self.ydata = ydata
        if not self.coursor_dragged:
            self.cursor_line.setValue(xpos)
        self.marker_plot.addPoints(x = [xpos],
                                   y = [ypos],
                                    symbol = '+',
                                    size = 25, pen = pg.mkPen(self.draw_color), 
                                    brush = self.draw_color)

class Plot(QtCore.QObject):
    """
    Class to hold plot widget, as well as all the plot items (curves, marker_arrows,etc)
    """
    user_xrange_change = QtCore.Signal(float, float)

    def __init__(self, controller, layout):
        super(Plot, self).__init__()

        self.controller = controller
        controller.state_change.connect(self.state_changed)
        # initialize main fft window

        self.freq_axis = RTSAFrequencyAxisItem()
        self.window = pg.PlotWidget(axisItems = dict(bottom = self.freq_axis))
        self.window.setMenuEnabled(False)

        def widget_range_changed(widget, ranges):

            if not hasattr(ranges, '__getitem__'):
                return  # we're not intereted in QRectF updates
            self.user_xrange_change.emit(ranges[0][0], ranges[0][1])

        self.window.sigRangeChanged.connect(widget_range_changed)

        self.view_box = self.window.plotItem.getViewBox()
        self.view_box.setMouseEnabled(x = True, y = False)

        # initialize the y-axis of the plot
        self.window.setYRange(PLOT_BOTTOM, PLOT_TOP)
        labelStyle = fonts.AXIS_LABEL_FONT

        self.window.setLabel('left', 'Power', 'dBm', **labelStyle)

        # initialize trigger lines
        self.amptrig_line = pg.InfiniteLine(pos = -100, angle = 0, movable = True)
        self.freqtrig_lines = pg.LinearRegionItem()
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
            self.markers.append(Marker(self, name, colors.WHITE_NUM))

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
        self.connect_plot_controls()

    def connect_plot_controls(self):
        def new_trigger_freq():
            self.controller.apply_device_settings(trigger = {'type': 'LEVEL',
                                                            'fstart': min(self.freqtrig_lines.getRegion()),
                                                            'fstop': max(self.freqtrig_lines.getRegion()),
                                                            'amplitude': self.gui_state.device_settings['trigger']['amplitude']})
        def new_trigger_amp():
            self.controller.apply_device_settings(trigger = {'type': 'LEVEL',
                'fstart': self.gui_state.device_settings['trigger']['fstart'],
                'fstop': self.gui_state.device_settings['trigger']['fstop'],
                'amplitude': self.amptrig_line.value()})
        # update trigger settings when ever a line is changed
        self.freqtrig_lines.sigRegionChangeFinished.connect(new_trigger_freq)
        self.amptrig_line.sigPositionChangeFinished.connect(new_trigger_amp)

    def state_changed(self, state, changed):
        self.gui_state = state
        if 'device_settings.trigger' in changed:
            if 'NONE' in state.device_settings['trigger']['type']:
                self.remove_trigger()
            elif 'LEVEL' in state.device_settings['trigger']['type']:

                self.add_trigger(state.device_settings['trigger']['fstart'],
                                state.device_settings['trigger']['fstop'],
                                state.device_settings['trigger']['amplitude'])
                for m in self.markers:
                    if m.enabled:
                        m.remove_marker(self)
                        m.add_marker(self)
        if 'center' in changed:
            self.controller.apply_device_settings(trigger = {'type': 'None',
                    'fstart': self.gui_state.device_settings['trigger']['fstart'],
                    'fstop': self.gui_state.device_settings['trigger']['fstop'],
                    'amplitude': self.amptrig_line.value()})
            self.remove_trigger()
            self.persistence_window.reset_plot()
            for trace in self.traces:
                trace.clear_data()
        if 'mode' in changed:
            self.update_iq_range = True
            self.iq_window.setYRange(IQ_PLOT_YMIN, IQ_PLOT_YMAX)


        if set(changed).intersection(PERSISTENCE_RESETTING_CHANGES):
            self.persistence_window.reset_plot()

    def add_trigger(self,fstart, fstop, amplitude):
        self.amptrig_line.blockSignals(True)
        self.freqtrig_lines.blockSignals(True)
        if not self._trig_enable:
            self.freqtrig_lines.setRegion([float(fstart),float(fstop)])
            self.window.addItem(self.freqtrig_lines)
            self.window.addItem(self.amptrig_line)
            self._trig_enable = True
        else:
            self.amptrig_line.setValue(amplitude)
            self.freqtrig_lines.setRegion([float(fstart),float(fstop)])

        self.amptrig_line.blockSignals(False)
        self.freqtrig_lines.blockSignals(False)

    def remove_trigger(self):
        self.window.removeItem(self.amptrig_line)
        self.window.removeItem(self.freqtrig_lines)
        self._trig_enable = False

    def center_view(self, fstart, fstop, min_level=None, ref_level=None):
        b = self.window.blockSignals(True)
        self.window.setXRange(float(fstart), float(fstop), padding=0)
        if min_level is not None:
            self.window.setYRange(min_level, ref_level)
            self.persistence_window.setYRange(min_level, ref_level)
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

    def update_markers(self):
        for m in self.markers:
            if m.enabled:
                trace = self.traces[m.trace_index]
                m.update_pos(trace.freq_range, trace.data)

    def update_iq_plots(self, data):

        trace = self.traces[0]
        if not (trace.write or trace.max_hold or trace.min_hold or trace.store):
            return

        if data.stream_id == VRT_IFDATA_I14Q14:
            data = data.data.numpy_array()
            i_data = np.array(data[:,0], dtype=float)/ZIF_BITS
            q_data = np.array(data[:,1], dtype=float)/ZIF_BITS
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
            data_payload = data.data.numpy_array()
            i_data = np.array(data_payload, dtype=float)

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
