import pyqtgraph as pg
import numpy as np
from PySide import QtCore
from pyrf.gui import colors
from pyrf.units import M
from pyrf.numpy_util import calculate_channel_power
LARGE_NEGATIVE_NUMBER = -900000

# minimum size allowed for auto peak
MIN_AUTO_POS_SIZE = 1000
class triggerControl(pg.ROI):
    """
    Class to represent the trigger controls in the plot
    """
    # sigHovering = QtCore.Signal(object)
    # sigHoveringFinished = QtCore.Signal(object)
    sigNewTriggerRange = QtCore.Signal(object)
    def __init__(self):
        super(triggerControl, self).__init__(pos=(0,0))

        self.normal_pen = pg.mkPen(color = colors.WHITE_NUM, width= 2)
        self.setPen(self.normal_pen)
        self.hover_pen = pg.mkPen(color = colors.LIME_NUM, width= 2)
        self.fstart = 0
        self.fstop = 0
        self.amplitude = 0

        self.init_lines()
        self.sigRegionChangeFinished.connect(self.new_trigger)
        self.sigRegionChangeStarted.connect(self.begin_changing)

    def begin_changing(self):
        for l in self.lines:
            l.blockSignals(True)

    def new_trigger(self):
        self.fstart = self.pos().x()
        self.fstop = self.fstart + self.size().x()
        self.amplitude = self.size().y() + self.pos().y()
        self.fstart_line.setValue(self.fstart)

        self.fstop_line.setValue(self.fstop)
        self.amplitude_line.setValue(self.amplitude)
        self.sigNewTriggerRange.emit(self)
        for l in self.lines:
            l.blockSignals(False)

    def init_lines(self):
        self.lines = []
        cursor_pen = pg.mkPen((0,0,0,0), width = 50)
        self.fstart_line = InfiniteLine(pen = cursor_pen, pos = -100, angle = 90, movable = True)
        self.lines.append(self.fstart_line)

        self.fstop_line = InfiniteLine(pen = cursor_pen, pos = -100, angle = 90, movable = True)
        self.lines.append(self.fstop_line)

        self.amplitude_line = InfiniteLine(pen = cursor_pen, pos = -100, angle = 0, movable = True)
        self.lines.append(self.amplitude_line)

        for l in self.lines:
            def hovering():
                self.setPen(self.hover_pen)
                # l.setPen(self.hover_pen)
            def not_hovering():
                self.setPen(self.normal_pen)
                # l.setPen(cursor_pen)

            l.setHoverPen(cursor_pen)
            l.sigHovering.connect(hovering)
            l.sigHoveringFinished.connect(not_hovering)

        def changing_fstart():
            self.setPen(self.hover_pen)
            self.resize_trigger(self.fstart_line.value(),
                                self.fstop,
                                self.amplitude)
        self.fstart_line.sigPositionChanged.connect(changing_fstart)

        def finished_changing_fstart():
            self.setPen(self.normal_pen)
            self.sigNewTriggerRange.emit(self)
        self.fstart_line.sigPositionChangeFinished.connect(finished_changing_fstart)

        def changing_fstop():
            self.setPen(self.hover_pen)
            self.resize_trigger(self.fstart,
                                self.fstop_line.value(),
                                self.amplitude)
        self.fstop_line.sigPositionChanged.connect(changing_fstop)

        def finished_changing_fstop():
            self.setPen(self.normal_pen)
            self.sigNewTriggerRange.emit(self)
        self.fstop_line.sigPositionChangeFinished.connect(finished_changing_fstop)

        def changing_amp():
            self.setPen(self.hover_pen)
            self.resize_trigger(self.fstart,
                                self.fstop,
                                self.amplitude_line.value())
        self.amplitude_line.sigPositionChanged.connect(changing_amp)

        def finished_changing_amplitude():
            self.setPen(self.normal_pen)
            self.sigNewTriggerRange.emit(self)
        self.amplitude_line.sigPositionChangeFinished.connect(finished_changing_amplitude)

    def resize_trigger(self, start, stop, amp):
        self.blockSignals(True)
        self.fstart = start
        self.fstop = stop
        self.amplitude = amp
        span = stop - start
        self.setPos(((start), LARGE_NEGATIVE_NUMBER))
        self.setSize((span, (-1 * LARGE_NEGATIVE_NUMBER) - np.abs(amp)))
        self.fstart_line.setValue(start)

        self.fstop_line.setValue(stop)
        self.amplitude_line.setValue(amp)
        self.blockSignals(False)

    def setMouseHover(self, hover):

        if self.mouseHovering == hover:
            return
        self.mouseHovering = hover
        if hover:
            self.currentPen = self.hover_pen
        else:
            self.currentPen = self.pen
        self.update()
 
class Trace(object):
    """
    Class to represent a trace in the plot
    """

    def __init__(self,plot_area, controller, trace_name, trace_color, blank = False, write = False):
        self.name = trace_name
        self.blank = blank
        self.store = False
        self.data = None
        self.raw_packet = None
        self.freq_range = [0.0, 0.0]
        self.controller = controller
        controller.trace_change.connect(self.trace_changed)
        self.color = trace_color

        self.calc_channel_power = False
        self.channel_power = 0
        self.channel_power_range = [0.0, 0.0]
        self.curves = []
        self.plot_area = plot_area
        self.average_list = []
        self.average_factor = 5

    def clear(self):
        for c in self.curves:
            self.plot_area.spectral_plot.removeItem(c)
        self.curves = []

    def clear_data(self):
        self.average_list = []
        self.data = None

    def update_average_factor(self, factor):
        self.average_factor = factor
        self.average_list = []

    def compute_channel_power(self):

        if self.calc_channel_power and not self.blank:
            if min(self.channel_power_range) > min(self.freq_range) and max(self.channel_power_range) < max(self.freq_range):
                    if self.data is not None:
                        min_bin = (np.abs(self.freq_range-min(self.channel_power_range))).argmin()
                        max_bin = (np.abs(self.freq_range-max(self.channel_power_range))).argmin()
                        self.channel_power = calculate_channel_power(self.data[min_bin:max_bin])

    def update_curve(self, xdata, ydata, usable_bins, sweep_segments):

        if self.blank or self.store:
            return

        self.freq_range = xdata
        if self._trace_state[self.name]['mode'] == 'Max Hold':
            if (self.data is None or len(self.data) != len(ydata)):
                self.data = ydata
            self.data = np.maximum(self.data,ydata)

        elif self._trace_state[self.name]['mode'] == 'Min Hold':
            if (self.data is None or len(self.data) != len(ydata)):
                self.data = ydata
            self.data = np.minimum(self.data,ydata)

        elif self._trace_state[self.name]['mode'] == 'Live':
            self.data = ydata

        elif self._trace_state[self.name]['mode'] == 'Average':
            if len(self.average_list) >= self.average_factor:
                self.average_list.pop(0)
            if self.average_list:
                if len(ydata) != len(self.data):
                    self.average_list = []
            self.average_list.append(ydata)
            self.data = np.average(self.average_list, axis = 0)

        self.clear()
        self.compute_channel_power()

        if usable_bins:
            # plot usable and unusable curves
            i = 0
            edge_color = tuple([c / 3 for c in self.color])
            for start_bin, run_length in usable_bins:

                if start_bin > i:
                    c = self.plot_area.spectral_plot.plot(x=xdata[i:start_bin+1],
                        y=self.data[i:start_bin+1], pen=edge_color)
                    self.curves.append(c)
                    i = start_bin
                if run_length:
                    c = self.plot_area.spectral_plot.plot(x=xdata[i:i+run_length],
                        y=self.data[i:i+run_length], pen=self.color)
                    self.curves.append(c)
                    i = i + run_length - 1
            if i < len(xdata):
                c = self.plot_area.spectral_plot.plot(x=xdata[i:], y=self.data[i:],
                    pen=edge_color)
                self.curves.append(c)
        else:
            odd = True
            i = 0
            alternate_color = (
                max(0, self.color[0] - 60),
                max(0, self.color[1] - 60),
                min(255, self.color[2] + 60),)
            if sweep_segments is None:
                sweep_segments = [len(self.data)]
            for run in sweep_segments:
                c = self.plot_area.spectral_plot.plot(x=xdata[i:i + run],
                    y=self.data[i:i + run],
                    pen=self.color if odd else alternate_color)
                self.curves.append(c)
                i = i + run
                odd = not odd

    def trace_changed(self, trace, state, changed):
        self._trace_state = state
        if trace == self.name:
            if 'color' in changed:
                self.color = state[trace]['color']
            if 'clear' in changed:
                self.clear_data()
            if 'pause' in changed:
                self.store = state[trace]['pause']
            if 'mode' in changed:
                if state[trace]['mode'] == 'Off':
                    self.blank = True
                    self.clear_data()
                    self.clear()
                else:
                    self.blank = False
            if 'average' in changed:
                self.update_average_factor(state[trace]['average'])

class Marker(object):
    """
    Class to represent a marker on the plot
    """
    shape = 'd'
    size = 25
    def __init__(self, plot_area, marker_name, color, controller, delta = False):

        self.name = marker_name
        self.delta = delta
        self.marker_plot = pg.ScatterPlotItem()
        self.enabled = False
        self.freq_pos = None
        self.power_pos = None
        self.xdata = []
        self.ydata = []
        self.trace_index = 0
        self.color = color
        self.draw_color = color
        self.hovering = False
        self._plot = plot_area
        self.coursor_dragged = False
        self.controller = controller
        controller.marker_change.connect(self.marker_changed)
        controller.trace_change.connect(self.trace_changed)
        controller.state_change.connect(self.state_changed)

        self.cursor_pen = pg.mkPen((0,0,0,0), width = 40)
        self.cursor_line = InfiniteLine(pen = self.cursor_pen, pos = -100, angle = 90, movable = True)
        self.cursor_line.setHoverPen(pg.mkPen((0,0,0, 0), width = 40))

        self.cursor_line.sigDragged.connect(self.dragged)
        
        self.text_box = pg.TextItem(text = '12312444')
        # self.text_box.setFont("font-size: 30px;")
        def hovering():
            self.coursor_dragged = True
            self.draw_color = colors.MARKER_HOVER
            self.controller.apply_marker_options(self.name, ['hovering'], [True])
        self.cursor_line.sigHovering.connect(hovering)

        def not_hovering():
            self.coursor_dragged = False
            self.draw_color = color
            self.update_pos(self.xdata, self.ydata)
            self.controller.apply_marker_options(self.name, ['hovering'], [False])
        self.cursor_line.sigHoveringFinished.connect(not_hovering)


    def dragged(self):
        # determine freq of drag
        freq = self.cursor_line.value()
        self.freq_pos = freq
        self.coursor_dragged = True
        self.cursor_line.setPen(self.cursor_pen)
        self.draw_color = colors.MARKER_HOVER
        self.controller.apply_plot_options(marker_dragged = True)
        self.update_pos(self.xdata, self.ydata)
        self.controller.apply_marker_options(self.name, ['hovering', 'freq'], [True, self.freq_pos])
        
    def remove_marker(self):
        self._plot.removeItem(self.marker_plot)
        self._plot.removeItem(self.cursor_line)
        self._plot.removeItem(self.text_box)

    def add_marker(self):
        self._plot.addItem(self.marker_plot)
        self._plot.addItem(self.cursor_line)
        self._plot.addItem(self.text_box)

    def enable(self):

        self.enabled = True
        self.add_marker()
        self.controller.apply_plot_options(marker_dragged = True)

    def disable(self):
        self.enabled = False
        self.remove_marker()

    def marker_changed(self, marker, state, changed):

        self._marker_state = state
        if marker == self.name:
            self.trace_index 
            if 'trace' in changed:
                self.trace_index = state[marker]['trace']

            if 'enabled' in changed:
                if state[marker]['enabled']:
                    self.enable()
                else:
                    self.disable()
            if 'freq' in changed:
                    self.freq_pos = state[marker]['freq']
            if 'hovering' in changed or 'tab' in changed:
                if state[marker]['hovering'] or state[marker]['tab']:
                    self.draw_color = colors.MARKER_HOVER
                else:
                    self.draw_color = self.color
            if 'peak' in changed:
                self.find_peak()
            if 'peak_right' in changed:
                self.find_right_peak()
            if 'peak_left' in changed:
                self.find_left_peak()

    def trace_changed(self, trace, state, changed):
        self._trace_state = state

    def state_changed(self, state, changed):
        self._gui_state = state

    def update_data(self, xdata, ydata):
        self.xdata = xdata
        self.ydata = ydata

    def update_pos(self, xdata, ydata):

        # calculate scale offset for marker
        height = np.abs( max(self._plot.getViewBox().viewRange()[1]) - min(self._plot.getViewBox().viewRange()[1]))
        scale =  height * 0.01
        self.marker_plot.clear()
        self._plot.removeItem(self.marker_plot)
        self._plot.addItem(self.marker_plot)

        if len(xdata) <= 0 or len(ydata) <= 0:
            return

        if self.freq_pos is None:
            self.freq_pos = xdata[len(xdata) / 2]
            self.controller.apply_marker_options(self.name, ['freq'], [self.freq_pos])

        if xdata[0] <= self.freq_pos <= xdata[-1]:
            # find index of nearest frequency
            index = np.argmin(np.abs(xdata - self.freq_pos))
            self.ypos = np.max(ydata[max(0, index - 5): min(len(self.ydata) - 1, index + 5)])
        else:
            self.ypos = 0
        self.xdata = xdata
        self.ydata = ydata

        if  self.coursor_dragged or  self._marker_state[self.name]['tab']:
            brush_color = self.draw_color
            self.cursor_line.setValue(self.freq_pos)
        else:

            brush_color = self.draw_color + (20,)

        
        self.marker_plot.addPoints(x = [self.freq_pos],
                                   y = [self.ypos + scale],
                                    symbol =  self.shape,
                                    size = self.size, pen = pg.mkPen(self.draw_color),
                                    brush = brush_color)
        if self.delta:
            text = '*' + str(self.name + 1)
        else:
            text = str(self.name + 1)
        color_txt = 'rgb%s' % str(self.draw_color)
        t = '<font size="12" font face="verdana" bgcolor="%s">%s</font>' % (color_txt, text)
        self.text_box.setHtml(t)
        y_pos = self.ypos + (0.1 * height)
        self.text_box.setPos(self.freq_pos, y_pos)
        self.update_state_power()
        
    def update_state_power(self):
        if self.ypos == 0:
            power = None
        else:
            power = self.ypos
        self.controller.apply_marker_options(self.name, ['power'], [power])

    def find_peak(self):
        """
        move the marker to the maximum point of the spectrum
        """
        # do nothing if there is no data
        if len(self.xdata) == 0 or len(self.ydata) == 0:
            return
        # retrieve the min/max x-axis of the current window
        window_freq = self._plot.getViewBox().viewRange()[0]
        data_range = self.xdata
        if window_freq[-1] < data_range[0] or window_freq[0] > data_range[-1]:
            return

        min_index, max_index = np.searchsorted(data_range, (window_freq[0], window_freq[-1]))

        peak_value = np.max(self.ydata[min_index:max_index])
        data_index = np.where(self.ydata==peak_value)[0]
        self.freq_pos = self.xdata[data_index][0]
        self.controller.apply_marker_options(self.name, ['freq'], [self.freq_pos])

    def find_right_peak(self):
        """
        move the selected marker to the next peak on the right
        """
        # do nothing if there is no data
        if len(self.xdata) == 0 or len(self.ydata) == 0:
            return

        # retrieve the min/max x-axis of the current window
        window_freq = self._plot.getViewBox().viewRange()[0]

        if self.freq_pos >= max(window_freq):
            return

        min_index = np.min(np.where(self.xdata >= self.freq_pos)) + 4
        max_index = len(self.xdata) - 1

        # determine if edge is reached
        if min_index >= max_index:
            return

        data_index = np.where(self.ydata == max(self.ydata[min_index:max_index]))[0]
        new_pos = self.xdata[data_index]
        if new_pos > max(self.xdata):
            return
        else:
            self.freq_pos = new_pos[0]
        self.controller.apply_marker_options(self.name, ['freq'], [self.freq_pos])

    def find_left_peak(self):
        """
        move the selected marker to the next peak on the left
        """
        # do nothing if there is no data
        if len(self.xdata) == 0 or len(self.ydata) == 0:
            return

        # retrieve the min/max x-axis of the current window
        window_freq = self._plot.getViewBox().viewRange()[0]

        if self.freq_pos >= max(window_freq):
            return

        min_index = 0
        max_index = np.min(np.where(self.xdata >= self.freq_pos)) - 4

        # determine if edge is reached
        if max_index <= 0:
            return

        data_index = np.where(self.ydata == max(self.ydata[min_index:max_index]))[0]
        new_pos = self.xdata[data_index][0]
        if new_pos > max(self.xdata):
            return
        else:
            self.freq_pos = new_pos

        self.controller.apply_marker_options(self.name, ['freq'], [self.freq_pos])

class DeltaMarker(Marker):
    shape = 't'
    size = 20
    def marker_changed(self, marker, state, changed):

        self._marker_state = state  
        if marker == self.name:
            if 'dtrace' in changed:
                self.trace_index = state[marker]['dtrace']

            if 'delta' in changed:
                if state[marker]['delta']:
                    self.enable()
                else:
                    self.disable()

            if 'dfreq' in changed:
                if not self.coursor_dragged:
                    self.freq_pos = state[marker]['dfreq']
            if 'hovering' in changed or 'tab' in changed:
                if state[marker]['hovering'] or state[marker]['tab']:
                    self.draw_color = colors.MARKER_HOVER
                else:
                    self.draw_color = self.color

    def state_changed(self, state, changed):
        self._gui_state = state

    def dragged(self):
        # determine freq of drag
        self.freq_pos  = self.cursor_line.value()
        self.coursor_dragged = True
        self.cursor_line.setPen(self.cursor_pen)
        self.draw_color = colors.MARKER_HOVER
        self.controller.apply_plot_options(marker_dragged = True)
        self.update_pos(self.xdata, self.ydata)
        self.controller.apply_marker_options(self.name, ['hovering', 'dfreq'], [True, self.freq_pos])

    def update_state_power(self):
        if self.ypos == 0:
            power = None
        else:
            power = self.ypos
        self.controller.apply_marker_options(self.name, ['dpower'], [power])
        
class InfiniteLine(pg.InfiniteLine):
    """
    Infinite Line with controls over the hover pen (feature will be available in pyqtgraph 0.9.9)
    """
    sigHovering = QtCore.Signal(object)
    sigHoveringFinished = QtCore.Signal(object)
    def setPen(self, *args, **kwargs):
        """Set the pen for drawing the line. Allowable arguments are any that are valid 
        for :func:`mkPen <pyqtgraph.mkPen>`."""
        self.pen = pg.mkPen(*args, **kwargs)
        if not self.mouseHovering:
            self.currentPen = self.pen
            self.update()

    def setHoverPen(self, *args, **kwargs):
        """Set the pen for drawing the line while the mouse hovers over it.
        Allowable arguments are any that are valid
        for :func:`mkPen <pyqtgraph.mkPen>`.

        If the line is not movable, then hovering is also disabled.

        Added in version 0.9.9."""
        self.hoverPen = pg.mkPen(*args, **kwargs)
        if self.mouseHovering:
            self.currentPen = self.hoverPen
            self.update()

    def boundingRect(self):
        #br = UIGraphicsItem.boundingRect(self)
        br = self.viewRect()
        ## add a 4-pixel radius around the line for mouse interaction.

        px = self.pixelLength(direction=pg.Point(1,0), ortho=True)  ## get pixel length orthogonal to the line
        if px is None:
            px = 0
        w = (max(4, self.pen.width()/2, self.hoverPen.width()/2)+1) * px
        br.setBottom(-w)
        br.setTop(w)
        return br.normalized()

    def hoverEvent(self, ev):
        if (not ev.isExit()) and self.movable and ev.acceptDrags(QtCore.Qt.LeftButton):
            self.setMouseHover(True)
        else:
            self.setMouseHover(False)

    def setMouseHover(self, hover):
        ## Inform the item that the mouse is (not) hovering over it
        if self.mouseHovering == hover:
            return
        self.mouseHovering = hover
        if hover:
            self.currentPen = self.hoverPen
            self.sigHovering.emit(self)
        else:
            self.currentPen = self.pen
            self.sigHoveringFinished.emit(self)
        self.update()
