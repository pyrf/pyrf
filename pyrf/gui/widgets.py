"""
General-purpose widgets
"""
from PySide import QtGui, QtCore
import pyqtgraph as pg
from pyrf.gui import colors
from pyrf.gui import fonts
from pyrf.units import M, G
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

    def stepBy(self, steps):
        """
        Force immediate change when using step buttons
        """
        rval = super(QDoubleSpinBoxPlayback, self).stepBy(steps)
        self.editingFinished.emit()

class SpectralWidget(QtGui.QWidget):
    """
    A widget based from the Qt widget with a layout that represents the Fstart/Fstop and Fcenter
    if the curret spectral plot
    """

    def __init__(self, controller):
        super(SpectralWidget, self).__init__()

        self.controller = controller
        controller.device_change.connect(self.device_changed)
        controller.state_change.connect(self.state_changed)

        self._create_controls()
        self.setLayout(QtGui.QGridLayout())
        self._build_layout()

    def _create_controls(self):
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.MinimumExpanding, QtGui.QSizePolicy.Fixed)

        self._fstart_label = QtGui.QLabel('FSTART')
        self._fstart_label.setSizePolicy(sizePolicy)
        self._fstart_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        self._fstart_label.setAlignment(QtCore.Qt.AlignCenter)

        self._fstop_label = QtGui.QLabel('FSTOP')
        self._fstop_label.setSizePolicy(sizePolicy)
        self._fstop_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        self._fstop_label.setAlignment(QtCore.Qt.AlignCenter)

        self._fcenter_label = QtGui.QLabel('FCENTER')
        self._fcenter_label.setSizePolicy(sizePolicy)
        self._fcenter_label.setStyleSheet(fonts.MARKER_LABEL_FONT % (colors.BLACK_NUM + colors.GREY_NUM))
        self._fcenter_label.setAlignment(QtCore.Qt.AlignCenter)

        self._mask_label = QtGui.QLabel()
        self._mask_label.setStyleSheet('background-color: black')
        self.window = pg.PlotWidget()
    def _build_layout(self):
        
        grid = self.layout()
        grid.setSpacing(0)
        grid.setHorizontalSpacing(0)

        grid.addWidget(self.window, 0, 0, 1, 4)
        grid.addWidget(self._mask_label, 1, 0, 1, 4)
        grid.addWidget(self._fstart_label, 1, 1, 1, 1)
        grid.addWidget(self._fcenter_label, 1, 2, 1, 1)
        grid.addWidget(self._fstop_label, 1, 3, 1, 1)

    def device_changed(self, dut):
        self.dut_prop = dut.properties

    def state_changed(self, state, changed):
        self.gui_state = state

        if 'span' in changed or 'center' in changed:
            if state.rfe_mode() in self.dut_prop.TUNABLE_MODES:
                center = state.center
            else:
                center = self.dut_prop.MAX_TUNABLE[state.rfe_mode()]
            fstart = center - (state.span/ 2)
            fstop = center + (state.span / 2)
            if int(center) > G:
                unit = 'GHz'
                div = G
            else:
                unit = 'MHz'
                div = M
            self._fstart_label.setText('Fstart (%s): %0.4f' % (unit, fstart / div))
            self._fcenter_label.setText('Fcenter (%s): %0.4f' % (unit, center / div))
            self._fstop_label.setText('Fstop (%s): %0.4f' % (unit, fstop / div))
