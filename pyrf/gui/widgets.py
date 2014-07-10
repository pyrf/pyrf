"""
General-purpose widgets
"""
from PySide import QtGui

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
