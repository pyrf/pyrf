import pyqtgraph as pg
PLOT_YMIN = -140
PLOT_YMAX = 20

class plot(object):
    """
    Class to hold plot widget, as well as all the plot items (curves, arrows,etc)
    """
    
    def __init__(self):
    
        self.window = pg.PlotWidget(name='pyrf_plot')
        
        # initialize the x-axis of the plot
        self.window.setLabel('bottom', text= 'Frequency', units = 'Hz', unitPrefix=None)

        # initialize the y-axis of the plot
        self.window.setYRange(PLOT_YMIN, PLOT_YMAX)
        self.window.setLabel('left', text = 'Power', units = 'dBm')
        
        # initialize fft curve
        self.fft_curve = self.window.plot(pen = 'g')
        self.amptrig_line = pg.InfiniteLine(pos = -100, angle = 0, movable = True)
        
        self.freqtrig_lines = None

        
    def add_trigger(self, layout):
        self.freqtrig_lines = pg.LinearRegionItem([layout.center_freq - 10e6,layout.center_freq + 10e6])
        self.freqtrig_lines.sigRegionChangeFinished.connect(layout.update_trig)
        self.window.addItem(self.amptrig_line)
        self.window.addItem(self.freqtrig_lines)
        self.amptrig_line.sigPositionChangeFinished.connect(layout.update_trig)