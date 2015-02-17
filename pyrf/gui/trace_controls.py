from collections import namedtuple

from PySide import QtGui, QtCore
from pyrf.gui import labels
from pyrf.gui import colors
from pyrf.gui.util import hide_layout
from pyrf.gui.fonts import GROUP_BOX_FONT
from pyrf.gui.widgets import (QCheckBoxPlayback, QDoubleSpinBoxPlayback, QComboBoxPlayback)
from pyrf.gui.gui_config import traceState
import numpy as np

REMOVE_BUTTON_WIDTH = 10
MAX_AVERAGE_FACTOR = 1000
DEFAULT_AVERAGE_FACTOR = 5
DEFAULT_TRACE = 0 # 0 indicates LIVE

TRACE_MODES = ['Live', 'Max Hold', 'Min Hold', 'Average', 'Off']

class TraceWidgets(namedtuple('TraceWidgets', """
    icon
    color_button
    draw
    hold
    clear
    average_label
    average_edit
    add
    remove
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
    """
    __slots__ = []
    __slots = []

class TraceControls(QtGui.QWidget):
    """
    A widget with a layout containing widgets that
    can be used to control the FFT plot's traces
    :param name: The name of the groupBox
    """
    def __init__(self, controller):
        super(TraceControls, self).__init__()

        self.controller = controller
        controller.state_change.connect(self.state_changed)
        controller.plot_change.connect(self.plot_changed)
        controller.trace_change.connect(self.trace_changed)
        self._trace_state = traceState
        self.setStyleSheet(GROUP_BOX_FONT)

        self.setLayout(QtGui.QGridLayout())
        self._create_controls()
        self._build_layout()

    def _create_controls(self):
        self._traces = []
        for num in range(len(colors.TRACE_COLORS)):
            self._traces.append(self._create_trace_widgets(num))

    def _create_trace_widgets(self, num):
        """
        :param num: index of this set of trace controls from 0 - 2

        :returns: a TraceWidgets namedtuple
        """
        icon = QtGui.QLabel()

        r, g, b = colors.TRACE_COLORS[num]
        self._update_banner_color(icon, r, g, b)

        color_button = QtGui.QPushButton()
        r, g, b = colors.TRACE_COLORS[num]
        self._update_button_color(color_button, r, g, b)

        def custom_color_clicked():
            color = QtGui.QColorDialog.getColor()
            # Don't update if color chosen is black
            if not (color.red(), color.green(), color.blue()) == colors.BLACK_NUM:
                self._update_banner_color(icon, color.red(), color.green(), color.blue())
                self._update_button_color(color_button, color.red(), color.green(), color.blue())
                color = (color.red(), color.green(), color.blue())
                trace_colors = {}
                self.controller.apply_trace_options(num, ['color'], [color])

        color_button.clicked.connect(custom_color_clicked)

        draw = QComboBoxPlayback()
        draw.setToolTip("Select data source")
        for i, val in enumerate(TRACE_MODES):
            draw.addItem(val)
        draw.setCurrentIndex(num)

        def draw_changed(index):
            self.controller.apply_trace_options(num, ['mode'], [draw.currentText()])
        draw.currentIndexChanged.connect(draw_changed)

        hold = QtGui.QCheckBox("Pause")
        hold.setToolTip("Pause trace updating")

        def hold_clicked():
            self.controller.apply_trace_options(num, ['pause'], [hold.isChecked()])
        hold.clicked.connect(hold_clicked)
        clear = QtGui.QPushButton("Clear Trace")
        clear.setToolTip("Refresh the data of the trace")

        def clear_clicked():
            self.controller.apply_trace_options(num, ['clear'], [None])
        clear.clicked.connect(clear_clicked)

        average_label = QtGui.QLabel("Captures:")

        average_edit = QtGui.QSpinBox()
        average_edit.setRange(2, MAX_AVERAGE_FACTOR)
        average_edit.setValue(DEFAULT_AVERAGE_FACTOR)

        def average_changed():
            self.controller.apply_trace_options(num, ['average'], [average_edit.value()])
        average_edit.valueChanged.connect(average_changed)
        average_edit.hide()

        add_trace = QtGui.QPushButton("+ Trace")
        add_trace.setToolTip("Enable this trace")

        def add_trace_clicked():
            draw.setCurrentIndex(DEFAULT_TRACE)
            draw_changed(DEFAULT_TRACE)
            self.controller.apply_trace_options(num, ['mode'], ['Live'])
            if hold.isChecked():  # force hold off
                hold.click()
            self._build_layout()
        add_trace.clicked.connect(add_trace_clicked)

        remove_trace = QtGui.QPushButton("-")
        remove_trace.setMinimumWidth(REMOVE_BUTTON_WIDTH)
        remove_trace.setToolTip("Disable this trace")

        def remove_trace_clicked():
            self.blank_trace(num)
            self.controller.apply_trace_options(num, ['mode'], ['Off'])
            self._build_layout()
        remove_trace.clicked.connect(remove_trace_clicked)

        return TraceWidgets(icon, color_button, draw, hold, clear,
                            average_label, average_edit,
                            add_trace, remove_trace)

    def _update_banner_color(self, icon, r, g, b):
            color = QtGui.QColor()
            color.setRgb(r, g, b)
            pixmap = QtGui.QPixmap(320, 2)
            pixmap.fill(color)
            icon.setPixmap(pixmap)
            return icon

    def _update_button_color(self, color_button, r, g, b):
            button_icon = QtGui.QIcon()
            color = QtGui.QColor()
            color.setRgb(r, g, b)
            pixmap = QtGui.QPixmap(50, 50)
            pixmap.fill(color)
            button_icon.addPixmap(pixmap)
            color_button.setIcon(button_icon)
            return color_button

    def _build_layout(self):
        """
        rebuild grid layout based on marker and trace states
        """
        grid = self.layout()
        hide_layout(grid)
        def show(widget, y, x, h, w):
            grid.addWidget(widget, y, x, h, w)
            widget.show()

        def add_trace_widgets(trace_widgets, row):
            show(trace_widgets.icon, row, 0, 1, 7)
            row = row + 1
            show(trace_widgets.color_button, row, 0, 1, 1)
            show(trace_widgets.draw, row, 1, 1, 2)
            show(trace_widgets.hold, row, 3, 1, 2)
            show(trace_widgets.clear, row, 5, 1, 2)

            row = row + 1

            show(trace_widgets.average_label, row, 1, 1, 2)
            show(trace_widgets.average_edit, row, 3, 1, 2)
            if self._trace_state[trace_index]['mode'] != 'Average':
                trace_widgets.average_label.hide()
                trace_widgets.average_edit.hide()
            return row + 1

        def add_trace_off_widgets(trace_widgets, row):
            show(trace_widgets.icon, row, 0, 1, 7)
            row = row + 1
            show(trace_widgets.color_button, row, 0, 1, 1)
            show(trace_widgets.add, row, 1, 1, 2)
            return row + 1
        row = 0
        for trace_index, widgets in enumerate(self._traces):
            if self._trace_state[trace_index]['mode'] == 'Off':
                row = add_trace_off_widgets(widgets, row)
                continue
            row = add_trace_widgets(widgets, row)

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
                
    def trace_changed(self, trace, state, changed):
        self._trace_state = state
       
        if 'color' in changed:
            color = state[trace]['color']
            self._update_banner_color(self._traces[trace].icon, 
                                    color[0], 
                                    color[1],
                                    color[2])
            self._update_button_color(self._traces[trace].color_button,
                                    color[0], 
                                    color[1],
                                    color[2])
        if 'mode' in changed:
            mode = state[trace]['mode']
            self._traces[trace].draw.quiet_update(TRACE_MODES, mode)
            if mode == 'Average':
                self._traces[trace].average_label.show()
                self._traces[trace].average_edit.show()
            elif mode == 'Off' or mode == 'Live':
                self._build_layout()
            else:
                self._traces[trace].average_label.hide()
                self._traces[trace].average_edit.hide()
        if 'pause' in changed:
            check_state = QtCore.Qt.CheckState()
            if state[trace]['pause']:
                check_state = QtCore.Qt.CheckState(2)
            else:
                check_state = QtCore.Qt.CheckState(0)
            self._traces[trace].hold.setCheckState(check_state)

    def plot_changed(self, state, changed):
        self.plot_state = state

    def showEvent(self, event):
        self.activateWindow()
