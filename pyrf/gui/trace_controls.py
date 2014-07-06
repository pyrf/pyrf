from PySide import QtGui, QtCore
from pyrf.gui import labels
from pyrf.gui import colors
from pyrf.gui.util import update_marker_traces

import numpy as np

PLOT_YMIN = -140
PLOT_YMAX = 0

class TraceControls(QtGui.QGroupBox):
    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to control the FFT plot's traces
    :param name: The name of the groupBox
    """
    def __init__(self, plot, name="Trace Control"):
        super(TraceControls, self).__init__()

        self._plot = plot
        self.setTitle(name)
        self._marker_trace = None

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

        self.trace_attr['store'].clicked.connect(self._store_trace)
        self.trace_attr['max_hold'].clicked.connect(self.max_hold)
        self.trace_attr['min_hold'].clicked.connect(self.min_hold)
        self.trace_attr['write'].clicked.connect(self.trace_write)
        self.trace_attr['blank'].clicked.connect(self.blank_trace)
        self.trace_tab.currentChanged.connect(self._trace_tab_change)

    def _trace_tab_change(self):
        """
        change the selected trace
        """
        trace = self._plot.traces[self.trace_tab.currentIndex()]

        if trace.write:
            self.trace_attr['write'].click()
        elif trace.max_hold:
            self.trace_attr['max_hold'].click()
        elif trace.min_hold:
            self.trace_attr['min_hold'].click()
        elif trace.blank:
            self.trace_attr['blank'].click()

        if self._plot.traces[self.trace_tab.currentIndex()].store:
            state =  QtCore.Qt.CheckState.Checked
        else:
            state =  QtCore.Qt.CheckState.Unchecked
        self.trace_attr['store'].setCheckState(state)

    def max_hold(self):
        """
        disable/enable max hold on a trace
        """
        trace = self._plot.traces[self.trace_tab.currentIndex()]
        trace.write = False
        trace.max_hold = True
        trace.min_hold = False
        trace.blank = False
        self.trace_attr['store'].setEnabled(True)
        update_marker_traces(self._marker_trace, self._plot.traces)

    def min_hold(self):
        """
        disable/enable min hold on a trace
        """
        trace = self._plot.traces[self.trace_tab.currentIndex()]
        trace.write = False
        trace.max_hold = False
        trace.min_hold = True
        trace.blank = False
        self.trace_attr['store'].setEnabled(True)
        update_marker_traces(self._marker_trace, self._plot.traces)

    def trace_write(self):
        """
        disable/enable running FFT mode the selected trace
        """
        trace = self._plot.traces[self.trace_tab.currentIndex()]
        trace.write = True
        trace.max_hold = False
        trace.min_hold = False
        trace.blank = False
        self.trace_attr['store'].setEnabled(True)

        if self._marker_trace is not None:
            update_marker_traces(self._marker_trace, self._plot.traces)

    def blank_trace(self):
        """
        disable/enable the selected trace
        """
        if self.trace_attr['store'].checkState() is QtCore.Qt.CheckState.Checked:
            self.trace_attr['store'].click()

        self.trace_attr['store'].setEnabled(False)
        trace = self._plot.traces[self.trace_tab.currentIndex()]
        trace.write = False
        trace.max_hold = False
        trace.min_hold = False
        trace.blank = True
        trace.clear()
        trace.data = None

        count = 0
        for marker in self._plot.markers:
            if marker.enabled and marker.trace_index ==  self.trace_tab.currentIndex():
                marker.disable(self._plot)
                if count == self._marker_tab.currentIndex():
                    self._marker_check.click()
                    self._marker_tab.setCurrentIndex(0)
            count += 1
        update_marker_traces(self._marker_trace, self._plot.traces)

    def _store_trace(self):
        """
        store the current trace's data
        """
        if self.trace_attr['store'].checkState() is QtCore.Qt.CheckState.Checked:
            self._plot.traces[self.trace_tab.currentIndex()].store = True
        else:
            self._plot.traces[self.trace_tab.currentIndex()].store = False

    def _marker_control(self):
        """
        disable/enable marker
        """
        marker = self._plot.markers[self._marker_tab.currentIndex()]
        if self._marker_check.checkState() is QtCore.Qt.CheckState.Checked:

            self._marker_trace.setEnabled(True)
            if self._marker_trace.currentIndex() < 0:
                self._marker_trace.setCurrentIndex(0)
            marker.trace_index = int(self._marker_trace.currentText()) - 1
            marker.enable(self._plot)
        else:
            self._marker_trace.setEnabled(False)
            self._plot.markers[self._marker_tab.currentIndex()].disable(self._plot)

            self.marker_labels[self._marker_tab.currentIndex()].setText('')

    def _marker_trace_control(self):
        """
        change the trace that is currently associated with the marker
        """

        if self._marker_trace is not None:
            marker = self._plot.markers[self._marker_tab.currentIndex()]
            if not self._marker_trace.currentText() == '':
                marker.trace_index = int(self._marker_trace.currentText()) - 1


    def _marker_tab_change(self):
        """
        change the current selected marker
        """

        for marker in self._plot.markers:
            marker.selected = False
        marker = self._plot.markers[self._marker_tab.currentIndex()]
        if marker.enabled:
            if marker.trace_index == 2:
                if self._marker_trace.count() == 2:
                    index = 1
                else:
                    index = 2
                self._marker_trace.setCurrentIndex(index)
            else:
                self._marker_trace.setCurrentIndex(marker.trace_index)
            self._marker_trace.setEnabled(True)
            self._marker_check.setCheckState(QtCore.Qt.CheckState.Checked)
        else:
            self._marker_trace.setEnabled(False)

            self._marker_trace.setCurrentIndex(marker.trace_index)
            self._marker_check.setCheckState(QtCore.Qt.CheckState.Unchecked)
        marker.selected = True

    def _find_peak(self):
        """
        move the selected marker to the maximum point of the spectrum
        """
        marker = self._plot.markers[self._marker_tab.currentIndex()]

        # enable the marker if it is not already enabled
        if not marker.enabled:
            self._marker_check.click()

        # retrieve the min/max x-axis of the current window
        window_freq = self._plot.view_box.viewRange()[0]
        data_range = self.xdata
        if window_freq[-1] < data_range[0] or window_freq[0] > data_range[-1]:
            return

        min_index, max_index = np.searchsorted(data_range, (window_freq[0], window_freq[-1]))

        trace = self._plot.traces[marker.trace_index]
        peak_value = np.max(trace.data[min_index:max_index])
        marker.data_index = np.where(trace.data==peak_value)[0]

    def _find_right_peak(self):
        """
        move the selected marker to the next peak on the right
        """
        marker = self._plot.markers[self._marker_tab.currentIndex()]
        trace = self._plot.traces[marker.trace_index]
        pow_data = trace.data
        # enable the marker if it is not already enabled
        if not marker.enabled:
            self._marker_check.click()

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

        right_pow = pow_data[min_index:max_index]

        # calculate noise floor level by averaging the maximum 80% of the fft
        noise_floor = np.mean(np.sort(right_pow)[int(len(right_pow) * ( 0.8)):-1])

        peak_values = np.ma.masked_less(right_pow, noise_floor + self.plot_state.peak_threshold).compressed()
        if len(peak_values) == 0:
            return
        marker.data_index = np.where(pow_data==(peak_values[1 if len(peak_values) > 1 else 0]))[0]

    def _find_left_peak(self):
        """
        move the selected marker to the next peak on the left
        """
        marker = self._plot.markers[self._marker_tab.currentIndex()]
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
        left_pow = pow_data[min_index:max_index]

        # calculate noise floor level by averaging the maximum 80% of the fft
        noise_floor = np.mean(np.sort(left_pow)[int(len(left_pow) * ( 0.8)):-1])

        peak_values = np.ma.masked_less(left_pow, noise_floor + self.plot_state.peak_threshold).compressed()
        if len(peak_values) == 0:
            return
        marker.data_index = np.where(pow_data==(peak_values[-2 if len(peak_values) > 1 else -1]))[0]

    def _change_ref_level(self):
        """
        change the ref level (maximum of the y-axis) of the fft plot
        """
        try:
            ref = float(self._ref_level.text())
        except ValueError:
            self.ref_level.setText(str(self.plot_state.ref_level))
            return
        self.plot_state.ref_level = ref

        _center_plot_view(self)

    def _change_min_level(self):
        """
        change the min level of the fft plot
        """
        try:
            min = float(self._min_level.text())
        except ValueError:
            self.min_level.setText(str(self.plot_state.min_level))
            return
        self.plot_state.min_level = min
        _center_plot_view(self)



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


    def plot_controls(self):

        plot_group = QtGui.QGroupBox("Plot Control")
        self._plot_group = plot_group

        plot_controls_layout = QtGui.QVBoxLayout()

        first_row = QtGui.QHBoxLayout()
        marker_tab = QtGui.QTabBar()
        for marker in labels.MARKERS:
            marker_tab.addTab(marker)
        marker_tab.currentChanged.connect(self._marker_tab_change)
        first_row.addWidget(marker_tab)

        self._marker_tab = marker_tab
        self.control_widgets = [self._marker_tab]
        marker_check, marker_trace = self._make_marker_control()

        second_row = QtGui.QHBoxLayout()
        second_row.addWidget(marker_trace)
        second_row.addWidget(marker_check)

        third_row = QtGui.QHBoxLayout()
        third_row.addWidget(self._peak_left())
        third_row.addWidget(self._peak_control())
        third_row.addWidget(self._peak_right())

        fourth_row = QtGui.QHBoxLayout()
        ref_level, ref_label, min_level, min_label = self._ref_controls()

        fourth_row.addWidget(ref_label)
        fourth_row.addWidget(ref_level)
        fourth_row.addWidget(min_label)
        fourth_row.addWidget(min_level)

        fifth_row = QtGui.QHBoxLayout()
        fifth_row.addWidget(self._cf_marker())
        fifth_row.addWidget(self._center_control())

        plot_controls_layout.addLayout(first_row)
        plot_controls_layout.addLayout(second_row)
        plot_controls_layout.addLayout(third_row)
        plot_controls_layout.addLayout(fourth_row)
        plot_controls_layout.addLayout(fifth_row)
        plot_group.setLayout(plot_controls_layout)

        return plot_group

    def _make_marker_control(self):
        marker_trace = QtGui.QComboBox()
        marker_trace.setEnabled(False)
        marker_trace.setMaximumWidth(50)
        marker_trace.currentIndexChanged.connect(self._marker_trace_control)
        update_marker_traces(marker_trace, self._plot.traces)

        self._marker_trace = marker_trace
        marker_check = QtGui.QCheckBox('Enabled')
        marker_check.clicked.connect(self._marker_control)
        self._marker_check = marker_check

        self.control_widgets.append(self._marker_check)
        return marker_check,marker_trace

    def _peak_control(self):
        peak = QtGui.QPushButton('Peak')
        peak.setToolTip("[P]\nFind peak of the selected spectrum")
        peak.clicked.connect(self._find_peak)
        self._peak = peak
        self.control_widgets.append(self._peak)
        return peak

    def _peak_right(self):
        peak = QtGui.QPushButton('Peak Right')
        peak.setToolTip("Find peak right of current peak")
        peak.clicked.connect(self._find_right_peak)
        self._peak = peak
        self.control_widgets.append(self._peak)
        return peak

    def _peak_left(self):
        peak = QtGui.QPushButton('Peak Left')
        peak.setToolTip("Find peak left of current peak")
        peak.clicked.connect(self._find_left_peak)
        self._peak = peak
        self.control_widgets.append(self._peak)
        return peak

    def _center_control(self):
        center = QtGui.QPushButton('Recenter')
        center.setToolTip("[C]\nCenter the Plot View around the available spectrum")
        center.clicked.connect(lambda: self._plot.center_view(min(self.xdata),
                                                            max(self.xdata),
                                                            min_level = int(self._min_level.text()),
                                                            ref_level = int(self._ref_level.text())))
        self._center_bt = center
        self.control_widgets.append(self._center_bt)
        return center

    def _cf_marker(self):
        cf_marker = QtGui.QPushButton('Marker to Center Frequency')
        cf_marker.setToolTip("Center the frequency on the current marker")

        def cf_marker_click():
            current_marker = self._marker_tab.currentIndex()
            marker = self._plot.markers[current_marker]

            if marker.enabled:
                self.controller.apply_settings(center=
                    self.xdata[marker.data_index])
                marker.data_index = len(self.pow_data)/2
        cf_marker.clicked.connect(cf_marker_click)

        self.cf_marker = cf_marker
        self.control_widgets.append(self.cf_marker)
        return cf_marker

    def _ref_controls(self):
        ref_level = QtGui.QLineEdit(str(PLOT_YMAX))
        ref_level.returnPressed.connect(lambda: self._plot.center_view(min(self.xdata),
                                                                        max(self.xdata),
                                                                        min_level = int(self._min_level.text()),
                                                                        ref_level = int(self._ref_level.text())))
        self._ref_level = ref_level
        self.control_widgets.append(self._ref_level)
        ref_label = QtGui.QLabel('Maximum Level: ')

        min_level = QtGui.QLineEdit(str(PLOT_YMIN))
        min_level.returnPressed.connect(lambda: self._plot.center_view(min(self.xdata),
                                                                        max(self.xdata),
                                                                        min_level = int(self._min_level.text()),
                                                                        ref_level = int(self._ref_level.text())))
        min_label = QtGui.QLabel('Minimum Level: ')
        self._min_level = min_level
        self.control_widgets.append(self._min_level)
        return ref_level, ref_label, min_level, min_label

