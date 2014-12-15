from collections import namedtuple

from PySide import QtGui, QtCore
from pyrf.gui import labels
from pyrf.gui import colors
from pyrf.gui.util import hide_layout
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.widgets import (QCheckBoxPlayback, QDoubleSpinBoxPlayback)
import numpy as np

REMOVE_BUTTON_WIDTH = 10
MAX_AVERAGE_FACTOR = 1000
DEFAULT_AVERAGE_FACTOR = 5
DEFAULT_TRACE = 0 # 0 indicates LIVE
class TraceWidgets(namedtuple('TraceWidgets', """
    icon
    color_button
    draw
    hold
    clear
    average_label
    average
    add
    remove
    add_marker
    """)):
    """
    :param icon: color icon
    :param color_button: trace color button
    :param draw: draw combobox, including 'Live', 'Max', 'Min' options
    :param hold: pause checkbox
    :param clear: clear trace button
    :param average_label: average captures label
    :param average: average captures spinbox
    :param add: "+ trace" button
    :param remove: "- trace" button
    :param add_marker: "+ marker" button for adding a marker to this trace
    """
    __slots__ = []

class MarkerWidgets(namedtuple('MarkerWidgets', """
    marker
    center
    peak_left
    peak
    peak_right
    remove
    """)):
    """
    :param marker: marker name radio button assigned to button_group
    :param center: "center" button
    :param peak_left: "peak left" button
    :param peak: "peak" button
    :param peak_right: "peak right" button
    :param remove: "- marker" button
    """
    __slots = []

class TraceControls(QtGui.QWidget):
    """
    A widget with a layout containing widgets that
    can be used to control the FFT plot's traces
    :param name: The name of the groupBox
    """
    def __init__(self, controller, plot):
        super(TraceControls, self).__init__()

        self.controller = controller
        controller.state_change.connect(self.state_changed)
        controller.capture_receive.connect(self.capture_received)

        self._plot = plot
        self.setStyleSheet(GROUP_BOX_FONT)
        self._marker_trace = None

        self.setLayout(QtGui.QGridLayout())
        self._create_controls()
        self._build_layout()

    def _create_controls(self):
        self._traces = []
        for num in range(len(colors.TRACE_COLORS)):
            self._traces.append(self._create_trace_widgets(num))

        self._markers = []
        self._marker_group = QtGui.QButtonGroup()
        for num in (0, 1):
            self._markers.append(self._create_marker_widgets(num,
                self._marker_group))

    def _create_trace_widgets(self, num):
        """
        :param num: index of this set of trace controls from 0 - 2

        :returns: a TraceWidgets namedtuple
        """
        icon = QtGui.QLabel()
        def update_banner_color(r, g, b):
            color = QtGui.QColor()
            color.setRgb(r, g, b)
            pixmap = QtGui.QPixmap(320, 2)
            pixmap.fill(color)
            icon.setPixmap(pixmap)
        r, g, b = colors.TRACE_COLORS[num]
        update_banner_color(r, g, b)
        button_icon = QtGui.QIcon()

        color_button = QtGui.QPushButton()
        def update_button_color(r, g, b):
            color = QtGui.QColor()
            color.setRgb(r, g, b)
            pixmap = QtGui.QPixmap(50, 50)
            pixmap.fill(color)
            button_icon.addPixmap(pixmap)
            color_button.setIcon(button_icon)
        r, g, b = colors.TRACE_COLORS[num]
        update_button_color(r, g, b)

        def custom_color_clicked():
            color = QtGui.QColorDialog.getColor()
            # Don't update if color chosen is black
            if not (color.red(), color.green(), color.blue()) == colors.BLACK_NUM:
                update_banner_color(color.red(), color.green(), color.blue())
                update_button_color(color.red(), color.green(), color.blue())
                trace = self._plot.traces[num].color = (color.red(), color.green(), color.blue())
        color_button.clicked.connect(custom_color_clicked)

        draw = QtGui.QComboBox()
        draw.setToolTip("Select data source")
        for i, val in enumerate(['Live', 'Max Hold', 'Min Hold', 'Average', 'Off']):
            draw.addItem(val)
        draw.setCurrentIndex(num)  # default draw 0: Live, 1: Max, 2: Min
        def draw_changed(index):
            trace = self._plot.traces[num]
            # FIXME: why so many exclusive bools?
            trace.write = index == 0
            trace.max_hold = index == 1
            trace.min_hold = index == 2
            trace.average = index == 3
            trace.blank = index == 4
            if index == 3:
                average_label.show()
                average_edit.show()
            else:
                average_label.hide()
                average_edit.hide()

            if index == 4:  # 'Off'
                return remove_trace_clicked()
        draw.currentIndexChanged.connect(draw_changed)

        hold = QtGui.QCheckBox("Pause")
        hold.setToolTip("Pause trace updating")
        def hold_clicked():
            self._store_trace(num, hold.isChecked())
        hold.clicked.connect(hold_clicked)

        clear = QtGui.QPushButton("Clear Trace")
        clear.setToolTip("Refresh the data of the trace")
        def clear_clicked():
            trace = self._plot.traces[num]
            trace.clear_data()
        clear.clicked.connect(clear_clicked)

        average_label = QtGui.QLabel("Captures:")

        average_edit = QtGui.QSpinBox()
        average_edit.setRange(2, MAX_AVERAGE_FACTOR)
        average_edit.setValue(DEFAULT_AVERAGE_FACTOR)
        def average_changed():
            trace = self._plot.traces[num]
            trace.update_average_factor(average_edit.value())
        average_edit.valueChanged.connect(average_changed)
        average_edit.hide()

        add_trace = QtGui.QPushButton("+ Trace")
        add_trace.setToolTip("Enable this trace")
        def add_trace_clicked():
            draw.setCurrentIndex(DEFAULT_TRACE)
            draw_changed(DEFAULT_TRACE)
            if hold.isChecked():  # force hold off
                hold.click()
            self._build_layout()
        add_trace.clicked.connect(add_trace_clicked)

        remove_trace = QtGui.QPushButton("-")
        remove_trace.setMinimumWidth(REMOVE_BUTTON_WIDTH)
        remove_trace.setToolTip("Disable this trace")
        def remove_trace_clicked():
            self.blank_trace(num)
            self._build_layout()
        remove_trace.clicked.connect(remove_trace_clicked)

        add_marker = QtGui.QPushButton("+ Marker")
        add_marker.setToolTip("Add a marker to this trace")
        def add_marker_clicked():
            m = 0 if not self._plot.markers[0].enabled else 1
            self._plot.markers[m].enable(self._plot)
            self._plot.markers[m].trace_index = num
            if m == 0:
                self.controller.apply_plot_options(marker0 = True)
            else:
                self.controller.apply_plot_options(marker1 = True)
            self._build_layout()

        add_marker.clicked.connect(add_marker_clicked)

        return TraceWidgets(icon, color_button, draw, hold, clear,
                            average_label, average_edit,
                            add_trace, remove_trace, add_marker)

    def _create_marker_widgets(self, num, button_group):
        """
        :param num: index of this marker (currently 0 or 1)
        :param button_group: QButtonGroup for the marker radio buttons

        :returns: a MarkerWidgets namedtuple

        """
        label = QtGui.QLabel("M%d:" % (num + 1))

        center = QtGui.QPushButton("Center")
        center.setToolTip("Center the frequency on this marker")
        def center_clicked():
            marker = self._plot.markers[num]
            if marker.enabled:
                self.controller.apply_settings(center=
                    self.xdata[marker.data_index])
                marker.data_index = len(self.pow_data)/2
        center.clicked.connect(center_clicked)

        peak_left = QtGui.QPushButton("Peak Left")
        peak_left.setToolTip("Find peak left of the marker")
        def peak_left_clicked():
            self._find_left_peak(num)
        peak_left.clicked.connect(peak_left_clicked)

        peak = QtGui.QPushButton("Peak")
        peak.setToolTip("Find the peak of the selected spectrum")
        def peak_clicked():
            self._find_peak(num)
        peak.clicked.connect(peak_clicked)

        peak_right = QtGui.QPushButton("Peak Right")
        peak_right.setToolTip("Find peak right of the marker")
        def peak_right_clicked():
            self._find_right_peak(num)
        peak_right.clicked.connect(peak_right_clicked)

        remove_marker = QtGui.QPushButton("- Marker")
        remove_marker.setMinimumWidth(REMOVE_BUTTON_WIDTH)
        remove_marker.setToolTip("Remove this marker")
        def remove_marker_clicked():
            alt_mark = not num
            if num == 0:
                self.controller.apply_plot_options(marker0 = False)
            else:
                self.controller.apply_plot_options(marker1 = False)
            self._plot.markers[num].disable(self._plot)
            self._build_layout()
        remove_marker.clicked.connect(remove_marker_clicked)

        return MarkerWidgets(label, center, peak_left, peak, peak_right,
            remove_marker)

    def _build_layout(self):
        """
        rebuild grid layout based on marker and trace states
        """
        grid = self.layout()
        hide_layout(grid)
        def show(widget, y, x, h, w):
            grid.addWidget(widget, y, x, h, w)
            widget.show()

        def add_trace_widgets(trace_widgets, row, extra=False):
            show(trace_widgets.icon, row, 0, 1, 7)
            row = row + 1
            show(trace_widgets.color_button, row, 0, 1, 1)
            show(trace_widgets.draw, row, 1, 1, 2)
            show(trace_widgets.hold, row, 3, 1, 2)
            show(trace_widgets.clear, row, 5, 1, 2)

            row = row + 1

            show(trace_widgets.average_label, row, 1, 1, 2)
            show(trace_widgets.average, row, 3, 1, 2)
            if trace_widgets.draw.currentText() != 'Average':
                trace_widgets.average_label.hide()
                trace_widgets.average.hide()
            if extra:
                show(trace_widgets.add_marker, row, 5, 1, 2)
            return row + 1

        def add_trace_off_widgets(trace_widgets, row):
            show(trace_widgets.icon, row, 0, 1, 7)
            row = row + 1
            show(trace_widgets.color_button, row, 0, 1, 1)
            show(trace_widgets.add, row, 1, 1, 2)
            return row + 1

        def add_marker_widgets(marker_widgets, row):
            show(marker_widgets.marker, row, 0, 3,3)
            show(marker_widgets.peak, row, 1, 1, 2)
            show(marker_widgets.center, row, 3, 1, 2)
            show(marker_widgets.remove, row, 5, 1, 2)
            row = row + 1
            show(marker_widgets.peak_left, row, 1, 1, 2)
            show(marker_widgets.peak_right, row, 3, 1, 2)
            return row + 1

        extra_markers = any(not m.enabled for m in self._plot.markers)

        row = 0
        for trace_index, (trace, widgets) in enumerate(
                zip(self._plot.traces, self._traces)):
            if trace.blank:
                row = add_trace_off_widgets(widgets, row)
                continue
            row = add_trace_widgets(widgets, row, extra_markers)

            trace_markers = [
                i for (i, marker) in enumerate(self._plot.markers)
                if marker.enabled and marker.trace_index == trace_index]
            if trace_markers:
                for tm in trace_markers:
                    row = add_marker_widgets(self._markers[tm], row)

        grid.setColumnStretch(0, 4)
        grid.setColumnStretch(1, 4)
        grid.setColumnStretch(2, 8)
        grid.setColumnStretch(3, 4)
        grid.setColumnStretch(4, 8)
        grid.setColumnStretch(5, 4)
        grid.setColumnStretch(6, 8)

        grid.setRowStretch(row, 1)  # expand empty space at the bottom

        self.resize_widget()

    def resize_widget(self):
        self.setSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Maximum)

    def state_changed(self, state, changed):
        if 'device_settings.iq_output_path' in changed:
            if state.device_settings['iq_output_path'] == 'CONNECTOR':
                self.setEnabled(False)
            else:
                self.setEnabled(True)

    def capture_received(self, state, fstart, fstop, raw, power, usable, segments):
        # save x,y data for marker adjustments
        self.pow_data = power
        self.xdata = np.linspace(fstart, fstop, len(power))

    def blank_trace(self, num):
        """
        disable the selected trace
        """
        trace = self._plot.traces[num]
        trace.clear()
        trace.data = None
        for marker in self._plot.markers:
            if marker.trace_index == num:
                marker.disable(self._plot)

    def _store_trace(self, num, store):
        """
        store the current trace's data
        """
        self._plot.traces[num].store = bool(store)

    def _find_peak(self, num):
        """
        move the selected marker to the maximum point of the spectrum
        """
        marker = self._plot.markers[num]

        # retrieve the min/max x-axis of the current window
        window_freq = self._plot.view_box.viewRange()[0]
        data_range = self.xdata
        if window_freq[-1] < data_range[0] or window_freq[0] > data_range[-1]:
            return

        min_index, max_index = np.searchsorted(data_range, (window_freq[0], window_freq[-1]))

        trace = self._plot.traces[marker.trace_index]
        peak_value = np.max(trace.data[min_index:max_index])
        marker.data_index = np.where(trace.data==peak_value)[0]

    def _find_right_peak(self, num):
        """
        move the selected marker to the next peak on the right
        """
        marker = self._plot.markers[num]
        trace = self._plot.traces[marker.trace_index]
        pow_data = trace.data

        # retrieve the min/max x-axis of the current window
        window_freq = self._plot.view_box.viewRange()[0]
        if marker.data_index is None:
            marker.data_index = len(pow_data) / 2
        data_range = self.xdata[marker.data_index:-1]

        if len(data_range) == 0:
            return

        if window_freq[-1] < data_range[0] or window_freq[0] > data_range[-1]:
            return
        min_index, max_index = np.searchsorted(data_range, (window_freq[0], window_freq[-1])) + marker.data_index
        min_index += 1
        right_pow = max(pow_data[min_index:max_index])
        marker.data_index = np.where(pow_data==right_pow)[0]

    def _find_left_peak(self, num):
        """
        move the selected marker to the next peak on the left
        """
        marker = self._plot.markers[num]
        trace = self._plot.traces[marker.trace_index]
        pow_data = trace.data
        # enable the marker if it is not already enabled
        if not marker.enabled:
            self._marker_check.click()

        # retrieve the min/max x-axis of the current window
        window_freq = self._plot.view_box.viewRange()[0]
        if marker.data_index is None:
            marker.data_index = len(pow_data) / 2
        data_range = self.xdata[0:marker.data_index]

        if len(data_range) == 0:
            return
        if window_freq[-1] < data_range[0] or window_freq[0] > data_range[-1]:
            return

        min_index, max_index = np.searchsorted(data_range, (window_freq[0], window_freq[-1]))
        left_pow = max(pow_data[min_index:max_index])
        min_index -= 1
        marker.data_index = np.where(pow_data==left_pow)[0]

    def showEvent(self, event):
        self.activateWindow()
