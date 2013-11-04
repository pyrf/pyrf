import pyqtgraph as pg
import numpy as np
from pyrf.gui import colors
from pyrf.gui import labels

PLOT_YMIN = -160
PLOT_YMAX = 20

IQ_PLOT_YMIN = -1
IQ_PLOT_YMAX = 1

IQ_PLOT_XMIN = -1
IQ_PLOT_XMAX = 1

AXIS_OFFSET = 7
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
        self.data = None
        self.freq_range = None
        self.color = trace_color
        self.curve = plot_area.window.plot(pen = colors.TEAL_NUM)
        
    def update_curve(self,xdata, ydata):
  
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
        
        self.curve.setData(x = xdata, 
                            y = self.data,
                            pen = self.color)

class Marker(object):
    """
    Class to represent a marker on the plot
    """
    def __init__(self,plot_area, marker_name):

        self.name = marker_name
        self.marker_plot = pg.ScatterPlotItem()
        self.enabled = False
        self.selected = False
        self.data_index = None
        
        # index of trace associated with marker
        self.trace_index = 0
        
    def enable(self, plot):
        
        self.enabled = True
        plot.window.addItem(self.marker_plot)     
    
    def disable(self, plot):
        
        self.enabled = False
        plot.window.removeItem(self.marker_plot)
        self.data_index = None
        self.trace_index = 0
    def update_pos(self, xdata, ydata):
    
        self.marker_plot.clear()
        if self.data_index  == None:
           self.data_index = len(ydata) / 2 
   
        if self.data_index < 0:
           self.data_index = 0
            
        elif self.data_index >= len(ydata):
            self.data_index = len(ydata) - 1

        xpos = xdata[self.data_index]
        
        ypos = ydata[self.data_index]
        if self.selected:
            color = 'y'
        else: 
            color = 'w'
            
        self.marker_plot.addPoints(x = [xpos], 
                                   y = [ypos], 
                                    symbol = '+', 
                                    size = 20, pen = color, 
                                    brush = color)
class Plot(object):
    """
    Class to hold plot widget, as well as all the plot items (curves, marker_arrows,etc)
    """
    
    def __init__(self, layout):
    
        # initialize main fft window
        self.window = pg.PlotWidget(name='pyrf_plot')
        self.view_box = self.window.plotItem.getViewBox()
        # initialize the x-axis of the plot
        self.window.setLabel('bottom', text= 'Frequency', units = 'Hz', unitPrefix=None)

        # initialize the y-axis of the plot
        self.window.setYRange(PLOT_YMIN, PLOT_YMAX)
        self.window.setLabel('left', text = 'Power', units = 'dBm')
        
        # initialize fft curve
        self.fft_curve = self.window.plot(pen = colors.TEAL_NUM)
         
        # initialize trigger lines
        self.amptrig_line = pg.InfiniteLine(pos = -100, angle = 0, movable = True)
        self.freqtrig_lines = pg.LinearRegionItem()
        
        # update trigger settings when ever a line is changed
        self.freqtrig_lines.sigRegionChangeFinished.connect(layout.update_trig)
        self.amptrig_line.sigPositionChangeFinished.connect(layout.update_trig)
        
        self.grid(True)
        
        # IQ constellation window
        self.const_window = pg.PlotWidget(name='const_plot')
        self.const_plot = pg.ScatterPlotItem(pen = 'y')
        self.const_window.addItem(self.const_plot)
        self.const_window.setYRange(IQ_PLOT_YMIN, IQ_PLOT_YMAX)
        self.const_window.setXRange(IQ_PLOT_YMIN, IQ_PLOT_YMAX)  

        # IQ time domain  window
        self.iq_window = pg.PlotWidget(name='const_plot')
        self.iq_window.setYRange(IQ_PLOT_YMIN, IQ_PLOT_YMAX)
        self.i_curve = self.iq_window.plot(pen = 'r')
        self.q_curve = self.iq_window.plot(pen = 'g')

        
        # add traces
        self.traces = []
        first_trace = labels.TRACES[0]

        count = 0
        for trace_name, trace_color in zip(labels.TRACES, colors.TRACE_COLORS):
            if count == 0:
                blank_state = False
                write_state = True
            else:
                blank_state = True
                write_state = False
            self.traces.append(Trace(self,
                                    trace_name,
                                    trace_color, 
                                    blank = blank_state,
                                    write = write_state))
            count += 1

        self.window.addItem(self.traces[0].curve)
        
        self.markers = []
        for marker_name in labels.MARKERS:
            self.markers.append(Marker(self, marker_name))
            
    def add_trigger(self,fstart, fstop):
        self.freqtrig_lines.setRegion([fstart,fstop])
        self.window.addItem(self.amptrig_line)
        self.window.addItem(self.freqtrig_lines)
                
    def remove_trigger(self):
        self.window.removeItem(self.amptrig_line)
        self.window.removeItem(self.freqtrig_lines)
        
    def center_view(self,f,bw, min_level, ref_level):
        self.window.setXRange(f - (bw/2),f + (bw / 2))
        self.window.setYRange(min_level + AXIS_OFFSET, ref_level - AXIS_OFFSET)
        
    def grid(self,state):
        self.window.showGrid(state,state)
