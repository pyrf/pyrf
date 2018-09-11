#!/usr/bin/env python

from pyrf.devices.thinkrf import discover_wsa

wsas_on_network = discover_wsa()

print "---------------"
for wsa in wsas_on_network:
    print '\t', wsa["MODEL"], wsa["SERIAL"], wsa["FIRMWARE"], wsa["HOST"]
print "---------------"
