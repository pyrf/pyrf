#persistence_plot_widget.py

import time
import collections

from PySide import QtGui
import numpy as np
import pyqtgraph as pg

from waterfall_widget import WaterfallModel

#inject a familiar color scheme into pyqtgraph...
# - this makes it available in the stock gradient editor schemes.
# - we also want it at the top of the gradient editors... there's no stock
#    way in python to insert at the top of an ordereddict, so we rebuild it.
newGradients = collections.OrderedDict()
newGradients["rycb"] = {'ticks': [(0.00, ( 0, 0, 0, 255)),
                                  (0.15, (  0,   0, 255, 255)),
                                  (0.33, (  0, 255, 255, 255)),
                                  (0.66, (255, 255,   0, 255)),
                                  (1.00, (255,   0,   0, 255))],
                        'mode': 'rgb'}
for k, v in pg.graphicsItems.GradientEditorItem.Gradients.iteritems():
    newGradients[k] = v
pg.graphicsItems.GradientEditorItem.Gradients = newGradients


DECAY_TYPE_LINEAR_WITH_DATA = "linear_data_decay"

DECAY_WITH_DATA = "decay_with_data"
DECAY_WITH_TIME = "decay_with_time"

ALL_DECAY_TIMING = [DECAY_WITH_DATA,
                    #DECAY_WITH_TIME,
                    ]

def decay_fn_EXPONENTIAL(t_now, t_prev, decay_args, img_data):
    #t is either in time or is the number of arrays. We'll call this 'ticks'.
    #We don't care which it is, but the decay_args will specify the rate.
    half_life = decay_args[0]
    t_delta = float(t_now - t_prev)

    decay_frac = 0.5 ** (t_delta / half_life)
    img_data *= decay_frac
    return img_data


def decay_fn_LINEAR(t_now, t_prev, decay_args, img_data):
    #t is either in time or is the number of arrays. We'll call this 'ticks'.
    #We don't care which it is, but the decay_args will specify the rate.
    
    #half_life is odd for linear decay, but... consistency!
    half_life = decay_args[0]
    
    ticks_until_zero = 2*half_life
    decay_per_tick = 1.0 / ticks_until_zero
    
    t_delta = t_now - t_prev
    img_data -= (t_delta * decay_per_tick)
    return img_data #caller will clip the negatives


class PersistencePlotWidget(pg.PlotWidget):
    """Persistence plot widget."""
    def __init__(self, parent=None, background='default',
                 decay_timing = DECAY_WITH_DATA,
                 decay_fn = decay_fn_LINEAR,
                 decay_args = [10, ], #10 arrays until 0.5 decay (20 for full)
                 data_model = None, #a WaterfallModel (for now)
                 **kargs):
        pg.PlotWidget.__init__(self, parent, background, **kargs)

        self.setMenuEnabled(False)
        self.plotItem.getViewBox().setMouseEnabled(x = False, y = False)

        if decay_timing not in ALL_DECAY_TIMING:
            raise ValueError("Unsupported decay timing: %s" % decay_timing)
        
        self._decay_timing = decay_timing
        self._decay_fn = decay_fn
        self._decay_args = decay_args
        self._data_model = data_model
        
        self._persistent_img = None #the persistent image
        self._img_array = None #the persistent data (same shape as image)
        
        #The value of self._prev_t doesn't matter for the first round since the
        #first plot has nothing to decay...
        self._prev_t = 0
        
        #We will always have a gradient editor for providing our LUT, but it
        #may not be visible. It is referencable for layour, though... just grab
        #it after initializing the PersistencePlotWidget.
        self.gradient_editor = pg.GradientWidget(parent = self,
                                                 orientation = "left")
        self.gradient_editor.loadPreset("rycb") #we injected this scheme
        self.gradient_editor.sigGradientChanged.connect(self._onGradientChange)
        self._LUT_PTS = 256
        self._latest_lut = self._get_lut()
        
        if self._data_model:
            assert isinstance(data_model, WaterfallModel)
            try:
                self._data_model.sigNewDataRow.connect(self.onNewModelData)
            except AttributeError:
                raise ValueError("data_model must be a WaterfallModel") #for now
    
    def _onGradientChange(self):
        if self._persistent_img:
            self._persistent_img.setLookupTable(self._get_lut())
    
    def onNewModelData(self, data):
        (time_s, y_data, metadata) = data
        x_data = self._data_model.get_x_data()
        self.plot(x = x_data, y = y_data)
    
    def _get_lut(self):
        lut = self.gradient_editor.getLookupTable(self._LUT_PTS)
        #make sure that the lowest value drops to the background...
        lut[0] = self.backgroundBrush().color().toTuple()[:3]
        
        self._latest_lut = lut
        return lut
    
    def _InitPersistentImage(self):
        self._persistent_img = pg.ImageItem()
        self._persistent_img.setLookupTable(self._get_lut())
    
    def _UpdatePersistentImage(self):
        #safety check: if we have zero height or width we can't make an image...
        if min(self.size().toTuple()) <= 0:
            return
        
        #Make sure we have an image to start with!
        if self._persistent_img is None:
            self._InitPersistentImage()
        
        #Make a temporary blank image canvas to render the new plot to...
        tmp_plt_img = QtGui.QImage(self.size(), QtGui.QImage.Format_RGB32)
        
        #Draw the new plot to the temporary image...
        # - assumes it has already been plotted correctly (with plot())
        painter = QtGui.QPainter(tmp_plt_img)
        self.render(painter)
        
        #Get a pointer to the start of the 32-bit (RGB32) image data...
        ptr = tmp_plt_img.constBits()
        
        #Convert the image array to a numpy array...
        w = tmp_plt_img.width()
        h = tmp_plt_img.height()
        #arr = np.array(ptr).reshape(h, w, 4)
        new_img_array = np.fromstring(ptr,
                                      dtype = np.int32,
                                      count=(w*h))
        new_img_array = new_img_array.reshape(h, w)
        
        #Get rid of the temporary QPainter and QImage...
        # - removing the painter explicitly resolves a troubling segfault
        #    issue that Qt/PySide was having.
        del painter # <-- segfaults happen without this!
        del tmp_plt_img
        
        #Fix the array orientation...
        new_img_array = np.rot90(new_img_array, 3)
        
        #Normalize the array (0->1) for easy color scaling...
        new_img_array -= new_img_array.min()
        new_img_array /= new_img_array.max()
        
        #new_img_array *= (new_img_array > 0.5) #deletes old records
        
        #Figure out what period we are decaying over...
        t_prev = self._prev_t
        if self._decay_timing == DECAY_WITH_DATA:
            t_now = self._prev_t + 1
        else:
            t_now = time.time()
        self._prev_t = t_now
         
        #Initialize the persistent image if it does not exist...
        if self._img_array is None:
            self._img_array = np.zeros((w, h))
        else:
            #decay the old image...
            self._img_array = self._decay_fn(t_now,
                                             t_prev,
                                             self._decay_args,
                                             self._img_array)
        
        #Add the shiny new signal...
        self._img_array += new_img_array
        
        #Ensure we don't oversaturate...
        self._img_array = self._img_array.clip(0, 1)
        
        self._persistent_img.setImage(self._img_array)
        
        #Get the exact range in use by the plot to avoid image scaling...
        # - there is probably a cleaner way to get this vs digging down to the
        #    ViewBox state, but I can't find it at the moment.
        # - note that below we're using the (left_x, top_y, width, height) version
        #    of the QRectF constructor.
        #      - top *should* be ymax... but only ymin works.  This is odd!!
        (xmin, xmax), (ymin, ymax) = self.plotItem.vb.state["viewRange"]
        x = xmin
        y = ymin #should be ymax (!? - see above)
        width = (xmax - xmin)
        height = (ymax - ymin)
        
        #we clear every time, so need to re-add the image every time...
        self.addItem(self._persistent_img, ignoreBounds = True)
        self._persistent_img.setRect(pg.QtCore.QRectF(x, y, width, height))
    
    def plot(self, *args, **kwargs):
        kwargs["clear"] = True
        #pyqtgraph uses __getattr__ to get down to the PlotItem from a
        #PlotWidget, and this messes up inheritance. We need to go directly...
        ret = self.plotItem.plot(*args, **kwargs)
        
        self._UpdatePersistentImage()
        return ret
    
    def resizeEvent(self, event):
        #Our persistence is entirely contained within the image, so on resize
        #we can only really restart from scratch...
        # - TODO: if using a data model we could reconstruct from history
        self.reset_plot()
        super(PersistencePlotWidget, self).resizeEvent(event)

    def reset_plot(self):
        # Reset current plot
        self._img_array = None
        self._persistent_img = None
