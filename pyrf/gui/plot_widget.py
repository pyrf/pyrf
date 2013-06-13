import pyqtgraph as pg
import numpy as np
import constants

class plot(object):
    """
    Class to hold plot widget, as well as all the plot items (curves, marker_arrows,etc)
    """
    
    def __init__(self, layout):
    
        self.window = pg.PlotWidget(name='pyrf_plot')
        self.view_box = self.window.plotItem.getViewBox()
        # initialize the x-axis of the plot
        self.window.setLabel('bottom', text= 'Frequency', units = 'Hz', unitPrefix=None)

        # initialize the y-axis of the plot
        self.window.setYRange(constants.PLOT_YMIN, constants.PLOT_YMAX)
        self.window.setLabel('left', text = 'Power', units = 'dBm')
        
        # initialize fft curve
        self.fft_curve = self.window.plot(pen = constants.TEAL_NUM)
        self.marker_point = pg.ScatterPlotItem()
  
       # initialize marker
        self.marker_point = pg.ScatterPlotItem()

        # initialize delta
        self.delta_point = pg.ScatterPlotItem()
        
        # initialize trigger lines
        self.amptrig_line = pg.InfiniteLine(pos = -100, angle = 0, movable = True)
        self.freqtrig_lines = pg.LinearRegionItem()
        
        # update trigger settings when ever a line is changed
        self.freqtrig_lines.sigRegionChangeFinished.connect(layout.update_trig)
        self.amptrig_line.sigPositionChangeFinished.connect(layout.update_trig)
        self.grid(True)
    def add_marker(self):
        self.window.addItem(self.marker_point) 
        
    def remove_marker(self):
        self.window.removeItem(self.marker_point)
    
    def add_delta(self):
        self.window.addItem(self.delta_point) 
    
    def remove_delta(self):
        self.window.removeItem(self.delta_point)
        
    def add_trigger(self,fstart, fstop):
        self.freqtrig_lines.setRegion([fstart,fstop])
        self.window.addItem(self.amptrig_line)
        self.window.addItem(self.freqtrig_lines)
                
    def remove_trigger(self):
        self.window.removeItem(self.amptrig_line)
        self.window.removeItem(self.freqtrig_lines)
        
    def center_view(self,f,bw):
        self.window.setXRange(f - (bw/2),f + (bw / 2))
        self.window.setYRange(constants.PLOT_YMIN, constants.PLOT_YMAX)
        
    def grid(self,state):
        self.window.showGrid(state,state)