"""
General-purpose widgets
"""
from PySide import QtGui

class QComboBoxPlus(QtGui.QComboBox):
    """
    QComboBox with some extra features
    """
    def update_items_no_signal(self, items, select_item=None):
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
        self.setEnabled(True)
        self.blockSignals(b)

    def playback_value(self, value):
        """
        Remove all items but value and disable the control
        """
        self.update_items_no_signal([value])
        self.setEnabled(False)
