"""
General-purpose widgets
"""
from PySide import QtGui, QtCore
import pyqtgraph as pg
from pyrf.gui import colors
from pyrf.gui import fonts
from pyrf.units import M, G
from pyrf.gui.persistence_plot_widget import (PersistencePlotWidget,
                                              decay_fn_EXPONENTIAL)

class QComboBoxPlayback(QtGui.QComboBox):
    """
    QComboBox with playback features
    """
    def quiet_update(self, items=None, select_item=None):
        """
        Update all the items and select a new item in the combo box
        without sending any signals

        :param items: a list of strings to added to the combo box, if None,
                then attempt to update the current index to the select_item
        :param select_item: the string to select, if None then attempt
            to select the same string currently selected in the new list
            of items, if not present select the first item.
        """
        # if nothing is passed return
        if items is None and select_item is None:
            return
        
        # if no new items are passed, select the required item (select_item)
        if items is None:
            b = self.blockSignals(True)
            for i in range(self.count()):
                if self.itemText(i) == select_item:
                    self.setCurrentIndex(i)
                    self.blockSignals(b)
                    return

        # if new items are passed
        if select_item is None:
            select_item = self.currentText()
        b = self.blockSignals(True)
        self.clear()
        for i, item in enumerate(items):
            self.addItem(item)
            if item == select_item:
                self.setCurrentIndex(i)
        self.blockSignals(b)

    def quiet_update_pixel(self, colors, name, select_item = None):
        """
        Update all the item colors

        :param items: a list of tuple containing the colors
        :param select_item: the string to select, if None then attempt
            to select the same string currently selected in the new list
            of items, if not present select the first item.
        """

        if select_item is None:
            select_item = 0
        block = self.blockSignals(True)
        self.clear()
        for n, c in zip(name, colors):

            button_icon = QtGui.QIcon()
            color = QtGui.QColor()
            r, g, b = c
            color.setRgb(r, g, b)
            pixmap = QtGui.QPixmap(50, 50)
            pixmap.fill(color)
            button_icon.addPixmap(pixmap)
            self.addItem(button_icon, str(n))
            if n == select_item:
                self.setCurrentIndex(select_item)
        self.blockSignals(block)
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

    def stepBy(self, steps):
        """
        Force immediate change when using step buttons
        """
        rval = super(QDoubleSpinBoxPlayback, self).stepBy(steps)
        self.editingFinished.emit()

class PlotWindowWidget(QtGui.QWidget):
    """
    A widget based from the Qt widget with a layout that represents the Fstart/Fstop and Fcenter
    of the given plot window
    """

    def __init__(self, controller, plot, grad = False):
        super(PlotWindowWidget, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)
        controller.plot_change.connect(self.plot_changed)
        self._plot = plot
        self._grad = grad
        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()

    def _create_controls(self):
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)

        self._fcenter_label = QtGui.QLabel('Center')
        self._fcenter_label.setSizePolicy(sizePolicy)
        self._fcenter_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        self._fcenter_label.setAlignment(QtCore.Qt.AlignCenter)

        self._rbw_label = QtGui.QLabel('RBW: ')
        self._rbw_label.setSizePolicy(sizePolicy)
        self._rbw_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        self._rbw_label.setAlignment(QtCore.Qt.AlignCenter)

        self._span_label = QtGui.QLabel('Span')
        self._span_label.setSizePolicy(sizePolicy)
        self._span_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        self._span_label.setAlignment(QtCore.Qt.AlignCenter)

    def _build_layout(self):
        
        grid = self.layout()

        if self._grad:
            grid.addWidget(self._plot.gradient_editor)
        else:
            grid.setColumnMinimumWidth(0, 20)

        grid.addWidget(self._fcenter_label, 1, 2, 1, 1)
        grid.addWidget(self._rbw_label, 1, 1, 1, 1)
        grid.addWidget(self._span_label, 1, 3, 1, 1)

        grid.addWidget(self._plot, 0, 1, 1, 4)
        self.resize_widget()

    def device_changed(self, dut):
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state

        if 'span' in changed or 'center' in changed:
            if state.rfe_mode() in self.dut_prop.TUNABLE_MODES:
                center = state.center
            else:
                center = self.dut_prop.MAX_TUNABLE[state.rfe_mode()]
            if int(center) > G:
                unit = 'GHz'
                div = G
            else:
                unit = 'MHz'
                div = M
            self._fcenter_label.setText('Center: %0.4f %s' % (center / div, unit))
            self.update_span_label()

        if 'rbw' in changed:
            self.update_rbw_label()

    def plot_changed(self, state, changed):
        self.plot_state = state

    def update_rbw_label(self):
        rfe_mode = self.gui_state.rfe_mode()
        if rfe_mode == 'HDR':
            self._rbw_label.setText("RBW: %0.2f Hz" % (self.gui_state.rbw))
        else:
            self._rbw_label.setText("RBW: %0.2f kHz" % (self.gui_state.rbw / 1e3))

    def update_span_label(self):
        rfe_mode = self.gui_state.rfe_mode()
        if rfe_mode == 'HDR':
            self._span_label.setText("Span: %0.2f kHz" % (self.gui_state.span / 1e3))
        else:
            self._span_label.setText("Span: %0.2f MHz" % (self.gui_state.span/ M))

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)
