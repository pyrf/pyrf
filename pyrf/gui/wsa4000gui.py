import sys
from PySide import QtGui, QtCore
from pyrf.gui.gui import MainWindow, MainPanel
from pyrf.devices.thinkrf import WSA4000
from pyrf.connectors.twisted_async import TwistedConnector
from pyrf.numpy_util import compute_fft
from pyrf import twisted_util

import qt4reactor
from twisted.internet import defer

class TwistedMainWindow(MainWindow):

    def __init__(self, reactor):
        self._reactor = reactor
        super(TwistedMainWindow, self).__init__()

    def closeEvent(self, event):
        event.accept()
        self._reactor.stop()

    @defer.inlineCallbacks
    def open_device(self, name):
        # late import because installReactor is being used
        dut = WSA4000(connector=TwistedConnector(self._reactor))
        yield dut.connect(name)
        if '--reset' in sys.argv:
            yield dut.reset()

        self.dut = dut
        self.setCentralWidget(TwistedMainPanel(dut))
        self.setWindowTitle('PyRF: %s' % name)


class TwistedMainPanel(MainPanel):

    @defer.inlineCallbacks
    def initDUT(self):
        self.center_freq = yield self.dut.freq()
        self.decimation_factor = yield self.dut.decimation()

        yield self.dut.request_read_perm()
        while True:
            data, reflevel = yield twisted_util.read_data_and_reflevel(
                self.dut, self.points)
            self.screen.update_data(
                compute_fft(self.dut, data, reflevel),
                self.center_freq,
                self.decimation_factor)

    @defer.inlineCallbacks
    def _read_update_freq_edit(self):
        self._update_freq_edit() # once immediately in case of long delay
        self.center_freq = yield self.dut.freq()
        self._update_freq_edit()

    @defer.inlineCallbacks
    def _read_update_antenna_box(self):
        ant = yield self.dut.antenna()
        self._antenna_box.setCurrentIndex(ant - 1)

    @defer.inlineCallbacks
    def _read_update_bpf_box(self):
        bpf = yield self.dut.preselect_filter()
        self._bpf_box.setCurrentIndex(0 if bpf else 1)

    @defer.inlineCallbacks
    def _read_update_gain_box(self):
        gain = yield self.dut.gain()
        self._gain_box.setCurrentIndex(self._gain_values.index(gain))

    @defer.inlineCallbacks
    def _read_update_ifgain_box(self):
        ifgain = yield self.dut.ifgain()
        self._ifgain_box.setValue(int(ifgain))

    @defer.inlineCallbacks
    def _read_update_span_rbw_boxes(self):
        self.decimation_factor = yield self.dut.decimation()
        self._span_box.setCurrentIndex(
            self._decimation_values.index(self.decimation_factor))
        self._update_rbw_box()



def main():
    app = QtGui.QApplication(sys.argv)
    qt4reactor.install()
    # late import because installReactor is being used
    from twisted.internet import reactor
    ex = TwistedMainWindow(reactor)
    reactor.run()



