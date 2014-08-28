"""
General-purpose widgets
"""
from PySide import QtGui, QtCore
import pyqtgraph as pg
class QComboBoxPlayback(QtGui.QComboBox):
    """
    QComboBox with playback features
    """
    def quiet_update(self, items, select_item=None):
        """
        Update all the items and select a new item in the combo box
        without sending any signals

        :param items: a list of strings to added to the combo box
        :param select_item: the string to select, if None then attempt
            to select the same string currently selected in the new list
            of items, if not present select the first item.
        """
        if select_item is None:
            select_item = self.currentText()
        b = self.blockSignals(True)
        self.clear()
        for i, item in enumerate(items):
            self.addItem(item)
            if item == select_item:
                self.setCurrentIndex(i)
        self.blockSignals(b)

    def playback_value(self, value):
        """
        Remove all items but value and disable the control
        """
        self.quiet_update([value])
        self.setEnabled(False)


class QCheckBoxPlayback(QtGui.QCheckBox):
    """
    QCheckBox with playback features
    """
    def quiet_update(self, value):
        """
        Set the checkbox state without sending signals

        :param value: True/False
        """
        b = self.blockSignals(True)
        self.setChecked(value)
        self.blockSignals(b)

    def playback_value(self, value):
        """
        display value with checkbox disabled

        :param value: True/False
        """
        self.quiet_update(value)
        self.setEnabled(False)


class QDoubleSpinBoxPlayback(QtGui.QDoubleSpinBox):
    """
    QSpinBox with playback features
    """
    def quiet_update(self, minimum=None, maximum=None, value=None):
        """
        Set the spinbox range and value without sending signals

        :param minimum: float
        :param maximum: float
        :param value: float to set or None to leave unchanged
        """
        b = self.blockSignals(True)
        if minimum is not None:
            self.setMinimum(minimum)
        if maximum is not None:
            self.setMaximum(maximum)
        if value is not None:
            self.setValue(value)
        self.blockSignals(False)

    def playback_value(self, value):
        """
        display value and disable widget
        """
        self.quiet_update(value, value, value)
        self.setEnabled(False)

class infiniteLine(pg.InfiniteLine):
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