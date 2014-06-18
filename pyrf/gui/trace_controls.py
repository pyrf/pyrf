from PySide import QtGui
from pyrf.gui import labels
from pyrf.gui import colors
import control_util as cu
class TraceControls(QtGui.QGroupBox):
    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to control the FFT plot's traces
    :param name: The name of the groupBox
    """
    def __init__(self, name="Trace Controls"):
        super(TraceControls, self).__init__()

        self.setTitle(name)

        layout = QtGui.QVBoxLayout(self)
        
        # first row will contain the tabs
        first_row = QtGui.QHBoxLayout()

        # add tabs for each trace
        trace_tab = QtGui.QTabBar()
        count = 0
        for (trace,(r,g,b)) in zip(labels.TRACES, colors.TRACE_COLORS):
            trace_tab.addTab(trace)
            color = QtGui.QColor()
            color.setRgb(r,g,b)
            pixmap = QtGui.QPixmap(10,10)
            pixmap.fill(color)
            icon = QtGui.QIcon(pixmap)
            trace_tab.setTabIcon(count,icon)
            count += 1

        self.trace_tab = trace_tab
        first_row.addWidget(trace_tab)

        # second row contains the tab attributes
        second_row = QtGui.QHBoxLayout()
        max_hold, min_hold, write, store, blank  = self._trace_items()
        second_row.addWidget(max_hold)
        second_row.addWidget(min_hold)
        second_row.addWidget(write)
        second_row.addWidget(blank)
        second_row.addWidget(store)
        layout.addLayout(first_row)
        layout.addLayout(second_row) 
        self.setLayout(layout)

    def _trace_items(self):

        trace_attr = {}
        store = QtGui.QCheckBox('Store')
        store.setEnabled(False)
        trace_attr['store'] = store

        max_hold = QtGui.QRadioButton('Max Hold')
        trace_attr['max_hold'] = max_hold

        min_hold = QtGui.QRadioButton('Min Hold')
        trace_attr['min_hold'] = min_hold

        write = QtGui.QRadioButton('Write')
        trace_attr['write'] = write

        blank = QtGui.QRadioButton('Blank')
        trace_attr['blank'] = blank

        self.trace_attr = trace_attr
        self.trace_attr['write'].click()
        return max_hold, min_hold, write, store, blank
