from PySide import QtGui
from pyrf.devices.thinkrf import discover_wsa

class DiscoveryWidget(QtGui.QWidget):

    """
    A widget based from the Qt QGroupBox widget with a layout containing widgets that
    can be used to control the WSA4000/WSA5000
    :param name: The name of the groupBox
    :open_device_callback: A function that is called which returns the IP selected

    """
    def __init__(self, open_device_callback=None, name="Discovery Tool"):
        super(DiscoveryWidget, self).__init__()

        self._open_device_callback = open_device_callback

        self.setMinimumWidth(400)
        self.setWindowTitle('WSA Discovery To0l')
        dev_layout = QtGui.QVBoxLayout(self)

        first_row = QtGui.QHBoxLayout()
        first_row.addWidget(QtGui.QLabel("WSA5000 Units Available on Local Network"))

        second_row = QtGui.QHBoxLayout()
        second_row.addWidget(self._wsa_list())

        third_row = QtGui.QHBoxLayout()
        self._ip = QtGui.QLineEdit()
        third_row.addWidget(self._ip)    

        fourth_row = QtGui.QHBoxLayout()
        fourth_row.addWidget(self._ok_button())
        fourth_row.addWidget(self._refresh_button())
        fourth_row.addWidget(self._cancel_button())

        dev_layout.addLayout(first_row)
        dev_layout.addLayout(second_row)
        dev_layout.addLayout(third_row)
        dev_layout.addLayout(fourth_row)
        self.setLayout(dev_layout)
        self.layout = dev_layout

    def _wsa_list(self):
        self._list = QtGui.QListWidget()

        # add wsa connections to list
        wsas_on_network = discover_wsa()

        for wsa in wsas_on_network:
            self._list.addItem(" ".join([wsa["MODEL"],  wsa["SERIAL"], wsa["FIRMWARE"], wsa["HOST"]])) 
        self._list.currentItemChanged.connect(lambda: list_clicked())

        def list_clicked():
            if self._list.currentItem() is not None:
                self._ip.setText(self._list.currentItem().text()[-14:])
        return self._list

    def _ok_button(self):
        self._ok = QtGui.QPushButton("Ok")
        self._ok.clicked.connect(lambda: ok_clicked())

        def ok_clicked():
            if not self._ip.text() == "":
                if self._open_device_callback is not None:
                    self._open_device_callback(self._ip.text(), True)
                self.close()
        return self._ok

    def _refresh_button(self):
        self._refresh = QtGui.QPushButton("Refresh")
        self._refresh.clicked.connect(lambda: refresh_clicked())

        def refresh_clicked():
            self._list.clear()
            wsas_on_network = discover_wsa()
            for wsa in wsas_on_network:
                self._list.addItem(" ".join([wsa["MODEL"],  wsa["SERIAL"], wsa["FIRMWARE"], wsa["HOST"]])) 
        return self._refresh

    def _cancel_button(self):
        self._cancel = QtGui.QPushButton("Cancel")
        self._cancel.clicked.connect(lambda: cancel_clicked())

        def  cancel_clicked():
            if self._open_device_callback is not None:
                self._open_device_callback(self._ip.text(), False)
            self.close()
        return self._cancel

    def closeEvent(self, event):
        if self._open_device_callback is not None:
            self._open_device_callback(self._ip.text(), False)
