import pyqtgraph as pg
import numpy as np
from PySide import QtCore
from pyrf.gui import colors
from pyrf.units import M
from pyrf.numpy_util import calculate_channel_power
LARGE_NEGATIVE_NUMBER = -900000

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

        self.calc_channel_power = False
        self.channel_power = 0
        self.channel_power_range = []
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

    def compute_channel_power(self):
        if self.calc_channel_power and not self.blank:
            if min(self.channel_power_range) > min(self.freq_range) and max(self.channel_power_range) < max(self.freq_range):
                    min_bin = (np.abs(self.freq_range-min(self.channel_power_range))).argmin()
                    max_bin = (np.abs(self.freq_range-max(self.channel_power_range))).argmin()
                    self.channel_power = calculate_channel_power(self.data[min_bin:max_bin])

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
        self.compute_channel_power()

        if usable_bins:
            # plot usable and unusable curves
            i = 0
            edge_color = tuple([c / 3 for c in self.color])
            for start_bin, run_length in usable_bins:
                if start_bin > i:
                    c = self.plot_area.window.plot(x=xdata[i:start_bin+1],
                        y=self.data[i:start_bin+1], pen=edge_color)
                    self.curves.append(c)
                    i = start_bin
                if run_length:
                    c = self.plot_area.window.plot(x=xdata[i:i+run_length],
                        y=self.data[i:i+run_length], pen=self.color)
                    self.curves.append(c)
                    i = i + run_length - 1
            if i < len(xdata):
                c = self.plot_area.window.plot(x=xdata[i:], y=self.data[i:],
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
                c = self.plot_area.window.plot(x=xdata[i:i + run],
                    y=self.data[i:i + run],
                    pen=self.color if odd else alternate_color)
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
        self.cursor_line = InfiniteLine(pen = cursor_pen, pos = -100, angle = 90, movable = True)
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
        self._plot.window.removeItem(self.marker_plot)
        self._plot.window.addItem(self.marker_plot)

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
