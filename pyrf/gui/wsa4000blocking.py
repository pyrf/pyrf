import sys
from PySide import QtGui, QtCore
from pyrf.gui.gui import MainWindow, MainPanel
from pyrf.numpy_util import compute_fft
from pyrf.devices.thinkrf import WSA4000
from pyrf.util import read_data_and_reflevel

REFRESH_CHARTS = 0.05

class BlockingMainWindow(MainWindow):
    """
    Override the MainWindow methods that access twisted and use
    our BlockingMainPanel to do the same
    """
    def _get_reactor(self):
        return None

    def open_device(self, name):
        dut = WSA4000()
        dut.connect(name)
        dut.request_read_perm()
        if '--reset' in sys.argv:
            dut.reset()

        self.dut = dut
        self.setCentralWidget(BlockingMainPanel(dut))
        self.setWindowTitle('PyRF: %s' % name)

    def closeEvent(self, event):
        event.accept()

    def update_charts(self):
        if self.dut is None:
            return
        self.centralWidget().update_screen()


class BlockingMainPanel(MainPanel):
    """
    Override the MainPanel methods that use twisted
    """
    def initDUT(self):
        self.center_freq = self.dut.freq()
        self.decimation_factor = self.dut.decimation()
        data, reflevel = read_data_and_reflevel(self.dut)
        self.screen.update_data(
            compute_fft(self.dut, data, reflevel),
            self.center_freq,
            self.decimation_factor)

    def _read_update_antenna_box(self):
        self._antenna_box.setCurrentIndex(self.dut.antenna() - 1)

    def _read_update_bpf_box(self):
        self._bpf_box.setCurrentIndex(0 if self.dut.preselect_filter() else 1)

    def _read_update_gain_box(self):
        gain_index = self._gain_values.index(self.dut.gain())
        self._gain_box.setCurrentIndex(gain_index)

    def _read_update_ifgain_box(self):
        self._ifgain_box.setValue(int(self.dut.ifgain()))

    def _read_update_freq_edit(self):
        self.center_freq = self.dut.freq()
        self._update_freq_edit()

    def _read_update_span_rbw_boxes(self):
        self.decimation_factor = self.dut.decimation()
        self._span_box.setCurrentIndex(
            self._decimation_values.index(self.decimation_factor))
        self._update_rbw_box()



def main():
    app = QtGui.QApplication(sys.argv)
    ex = BlockingMainWindow()
    timer = QtCore.QTimer(ex)
    timer.timeout.connect(ex.update_charts)
    timer.start(REFRESH_CHARTS)
    sys.exit(app.exec_())


