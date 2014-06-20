from PySide import QtGui
import operator
from pyrf.devices.thinkrf import discover_wsa

class DiscoveryWidget(QtGui.QWidget):
    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to display WSA5000's available on the network
    :param name: The name of the groupBox
    :open_device_callback: A function that is called which returns the IP selected

    """
    def __init__(self, open_device_callback=None, name="Discovery Tool"):
        super(DiscoveryWidget, self).__init__()

        self._open_device_callback = open_device_callback

        self.setMinimumWidth(400)
        self.setWindowTitle(name)
        dev_layout = QtGui.QVBoxLayout(self)

        first_row = QtGui.QHBoxLayout()
        first_row.addWidget(QtGui.QLabel("Devices Detected on Local Network"))

        second_row = QtGui.QHBoxLayout()
        second_row.addWidget(self._wsa_list())

        ok = self._ok_button()

        third_row = QtGui.QHBoxLayout()
        third_row.addWidget(QtGui.QLabel("Manually Enter Device IP:"))
        third_row.addWidget(self._ip_edit())

        fourth_row = QtGui.QHBoxLayout()
        fourth_row.addWidget(ok)
        fourth_row.addWidget(self._refresh_button())
        fourth_row.addWidget(self._cancel_button())

        dev_layout.addLayout(first_row)
        dev_layout.addLayout(second_row)
        dev_layout.addLayout(third_row)
        dev_layout.addLayout(fourth_row)
        self.setLayout(dev_layout)
        self.layout = dev_layout

    def return_pressed(self):
        self._ok.click()

    def _wsa_list(self):
        self._list = QtGui.QListWidget()
        self._refresh_list()

        def list_clicked():
            if self._list.currentItem() is not None:
                self._ip.setText(self._list.currentItem().text().split(" ")[-1])
        self._list.currentItemChanged.connect(list_clicked)
        return self._list

    def _ip_edit(self):
        self._ip = QtGui.QLineEdit()
        self._ip.returnPressed.connect(self.return_pressed)
        return self._ip

    def _ok_button(self):
        self._ok = QtGui.QPushButton("Connect")
        def ok_clicked():
            if not self._ip.text() == "":
                if self._open_device_callback is not None:
                    self._open_device_callback(self._ip.text(), True)
                self.close()
        self._ok.clicked.connect(ok_clicked)
        return self._ok

    def _refresh_button(self):
        self._refresh = QtGui.QPushButton("Refresh")
        self._refresh.clicked.connect(self._refresh_list)
        return self._refresh

    def _cancel_button(self):
        self._cancel = QtGui.QPushButton("Cancel")
        def cancel_clicked():
            if self._open_device_callback is not None:
                self._open_device_callback(self._ip.text(), False)
            self.close()
        self._cancel.clicked.connect(cancel_clicked)
        return self._cancel

    def closeEvent(self, event):
        if self._open_device_callback is not None:
            self._open_device_callback(self._ip.text(), False)

    def _refresh_list(self):
        self._list.clear()
        wsas_on_network = discover_wsa()
        wsas_on_network.sort(key=operator.itemgetter('SERIAL'))
        for wsa in wsas_on_network:
            if "WSA5000" in wsa["MODEL"]:
                self._list.addItem(" ".join([wsa["MODEL"],  wsa["SERIAL"], wsa["FIRMWARE"], wsa["HOST"]]))
            elif "WSA4000" in wsa["MODEL"]:
                self._list.addItem(" ".join([wsa["MODEL"],  wsa["SERIAL"], wsa["HOST"]]))
