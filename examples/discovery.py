#!/usr/bin/env python

from pyrf.devices.thinkrf import discover_wsa

wsas_on_network = discover_wsa()

for wsa in wsas_on_network:
    print wsa["MODEL"], wsa["SERIAL"], wsa["FIRMWARE"], wsa["HOST"]
