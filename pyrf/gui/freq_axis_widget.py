#freq_axis_widget.py

import pyqtgraph as pg
from pyqtgraph.functions import siScale
from PySide import QtCore


class RTSAFrequencyAxisItem(pg.AxisItem):
    """A custom frequency axis for use in the RTSA GUI.
    
    This replaces the normal x tick labels with labls that indicate the start, center, and stop frequencies.
    
    To use it, this just needs to be added to the PlotItem constructor for
    the 'bottom' axisItem, as follows:
    
        axisItems=dict(bottom = RTSAFrequencyAxisItem())
    
    This axis works by:
      1) disabling the normal tick labels
           - showValues = False
      2) forcing there to be space available for our new labels
           - we override setHeight
      3) injecting new labels into the drawing flow where it would normally
          expect the "classic" tick labels
           - we intercept generateDrawSpecs

    """
    def __init__(self, **kwargs):
        kwargs["showValues"] = True
        self.labelUnits = "Hz"
        super(RTSAFrequencyAxisItem, self).__init__("bottom", **kwargs)
    
    def setHeight(self, h=None):
        #This is currently a hard coded hack to ensure that there is enough
        #vertical space for our fixed axis labels. It should really scale
        #according to text size (see super.setHeight for what it does,
        #although trying to modify it was finicky for some reason).
        self.setMaximumHeight(40)
        self.setMinimumHeight(40)
        self.picture = None
    
    def _getFrequencyTextSpecs(self):
        """Generates f axis labels for the overridden generateDrawSpecs.
        
        Expected form is a list of (QRectF, Alignment flags, unicode).
        
        """
        #TODO: proper/consistent sig fig handling would be nice
        
        freq_min, freq_max = self.range
        freq_center = (freq_max + freq_min) / 2.0
        
        #baseline QRect values...
        # - note that we don't clip, and we do properly align, so (w,h) is meh
        y = 22
        w = 30
        h = 20
        
        #Use common SI scaling, based on the low end...
        # - this avoids start being 600.00 MHz, and stop being 2.50 GHz
        #scale, si_prefix = siScale(freq_min)
        
        #set label contents...
        Qt = QtCore.Qt #space saver
        xpositions = [0, 0.5* self.width(), self.width() - 50] # -50 is a hack to fix pyrf_plot clipping issue
        labels = ["Start", "Center", "Stop"]
        freqs = [freq_min, freq_center, freq_max]
        alignments = [Qt.AlignLeft, Qt.AlignCenter, Qt.AlignRight]
        
        #Generate labels in a common way...
        textSpecs = [] #same as in superclass generateDrawSpecs
        for label, freq, alignment, x in zip(labels, freqs, alignments, xpositions):
            rect = QtCore.QRectF(x, y, w, h)
            textFlags = alignment | Qt.TextDontClip | Qt.AlignVCenter
            if freq <= 0:
                freq_txt = u"---"
            else:
                scale, si_prefix = siScale(freq)
                freq_txt = u"%.4f %sHz" % ((scale * freq), si_prefix)
            txt = u"%s = %s" % (label, freq_txt)
            textSpecs.append((rect, textFlags, txt))
        
        return textSpecs
    
    def generateDrawSpecs(self, p):
        #Force proper SI prefix usage...
        # - this is normally done in self.updateAutoSIPrefix, but pyqtgraph
        #    only enables tick label scaling when there is a genuine x axis
        #    label (and we don't have one).
        scale = self.scale
        xmin, xmax = self.range
        (scale, prefix) = siScale(max(abs(xmin * scale), abs(xmax * scale)))
        self.autoSIPrefixScale = scale
        
        #Get the standard tick labels...
        ret = list(super(RTSAFrequencyAxisItem, self).generateDrawSpecs(p))
        
        #Add in our start/centre/stop labels...
        ret[2].extend(self._getFrequencyTextSpecs())
        
        return tuple(ret)
