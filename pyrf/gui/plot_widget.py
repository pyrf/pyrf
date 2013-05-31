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

        # initialize max hold curve
        self.mhold_curve = pg.PlotCurveItem(pen = 'y')
        
        # keep values in mhold buff
        self.mhold_buf = np.zeros(1024)
        self.mhold_buf[0] = 0 
        self.mhold_curve.setData(self.mhold_buf)
        # initialize marker
        self.marker_point = None
        self.marker_arrow = None
        self.marker_label = pg.TextItem(anchor = (0,0))

        self.delta_point = None
        self.delta_arrow = None
        self.delta_label = pg.TextItem(anchor = (0,0))
        
        self.diff_label = pg.TextItem(anchor = (0,0))
        # initialize trigger lines
        self.amptrig_line = pg.InfiniteLine(pos = -100, angle = 0, movable = True)
        self.freqtrig_lines = pg.LinearRegionItem()
        
        # update trigger settings when ever a line is changed
        self.freqtrig_lines.sigRegionChangeFinished.connect(layout.update_trig)
        self.amptrig_line.sigPositionChangeFinished.connect(layout.update_trig)

    def add_marker(self):
        print 'got here'
        print self.mhold_buf[0] 
        if float(self.mhold_buf[0]) < 1:
            self.marker_point = pg.CurvePoint(self.fft_curve)
        self.marker_arrow =  pg.ArrowItem(pos=(0, 0), angle=-90, tailLen = 10, headLen = 30, pen = 'w', brush = (0,100,255)) 
        self.marker_arrow.setParentItem(self.marker_point)
        self.window.addItem(self.marker_point) 
        self.window.addItem(self.marker_label)
        
    def remove_marker(self):
        self.window.removeItem(self.marker_point)
        self.window.removeItem(self.marker_label)
    
    def add_delta(self):
        if self.mhold_buf[0] == 0:
            self.delta_point = pg.CurvePoint(self.fft_curve)
        self.delta_arrow =  pg.ArrowItem(pos=(0, 0), angle=-90, tailLen = 10, headLen = 30, pen = 'w', brush = (255,59,0)) 
        self.delta_arrow.setParentItem(self.delta_point)
        self.window.addItem(self.delta_point) 
        self.window.addItem(self.delta_label)
        self.window.addItem(self.diff_label)
    
    def remove_delta(self):
        self.window.removeItem(self.delta_point)
        self.window.removeItem(self.delta_label)
        self.window.removeItem(self.diff_label)
    
    def add_mhold(self, plot_state):
        if plot_state.marker:
            self.remove_marker()
            plot_state.disable_marker()
        if plot_state.delta:
            self.remove_delta()
            plot_state.disable_delta()
        self.mhold_buf[0] = 1
        self.delta_point = pg.CurvePoint(self.mhold_curve)
        self.marker_point = pg.CurvePoint(self.mhold_curve)
        self.window.addItem(self.mhold_curve)

    def remove_mhold(self,plot_state):
        if plot_state.marker:
            self.remove_marker()
        if plot_state.delta:
            self.remove_delta()
        self.mhold_buf[0] = 0
        self.window.removeItem(self.mhold_curve)
        plot_state.disable_marker()
        plot_state.disable_delta()
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