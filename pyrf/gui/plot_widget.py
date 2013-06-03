import pyqtgraph as pg
import numpy as np
PLOT_YMIN = -140
PLOT_YMAX = 20
INITIAL_FREQ = 2450e6
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
        self.window.setYRange(PLOT_YMIN, PLOT_YMAX)
        self.window.setLabel('left', text = 'Power', units = 'dBm')
        
        # initialize fft curve
        self.fft_curve = self.window.plot(pen = 'g')
        self.marker_point = pg.ScatterPlotItem()
        
        
        # initialize max hold curve
        self.mhold_curve = pg.PlotCurveItem(pen = 'y')
        
        # keep values in mhold buff
        self.mhold_buf = np.zeros(1024)
        self.mhold_buf[0] = 0 
        self.mhold_curve.setData(self.mhold_buf)
       
       # initialize marker
        self.marker_label = pg.TextItem(anchor = (0,0))
        self.marker_point = pg.ScatterPlotItem()

        # initialize delta
        self.delta_label = pg.TextItem(anchor = (0,0))
        self.delta_point = pg.ScatterPlotItem()

        self.diff_label = pg.TextItem(anchor = (0,0))
        
        # initialize trigger lines
        self.amptrig_line = pg.InfiniteLine(pos = -100, angle = 0, movable = True)
        self.freqtrig_lines = pg.LinearRegionItem()
        
        # update trigger settings when ever a line is changed
        self.freqtrig_lines.sigRegionChangeFinished.connect(layout.update_trig)
        self.amptrig_line.sigPositionChangeFinished.connect(layout.update_trig)

    def add_marker(self):
        self.window.addItem(self.marker_point) 
        self.window.addItem(self.marker_label)
        
    def remove_marker(self):
        self.window.removeItem(self.marker_point)
        self.window.removeItem(self.marker_label)
    
    def add_delta(self):
        self.window.addItem(self.delta_point) 
        self.window.addItem(self.delta_label)
        self.window.addItem(self.diff_label)
    
    def remove_delta(self):
        self.window.removeItem(self.delta_point)
        self.window.removeItem(self.delta_label)
        self.window.removeItem(self.diff_label)
    
    def add_mhold(self):
        self.window.addItem(self.mhold_curve)

    def remove_mhold(self):
        self.window.removeItem(self.mhold_curve)
    
    def add_trigger(self,f):
        self.freqtrig_lines.setRegion([f - 10e6, f + 10e6])
        self.window.addItem(self.amptrig_line)
        self.window.addItem(self.freqtrig_lines)
                
    def remove_trigger(self):
        self.window.removeItem(self.amptrig_line)
        self.window.removeItem(self.freqtrig_lines)
        
    def center_view(self,f,bw):
        self.window.setXRange(f - (bw/2),f + (bw / 2))
        self.window.setYRange(PLOT_YMIN, PLOT_YMAX)
        
    def grid(self,state):
        self.window.showGrid(state,state)