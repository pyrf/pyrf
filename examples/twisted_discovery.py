#!/usr/bin/env python

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
import struct
import platform

from pyrf.devices.thinkrf import (DISCOVERY_UDP_PORT, DISCOVERY_QUERY,
    parse_discovery_response)
from pyrf.windows_util import get_broadcast_addresses

WAIT_TIME = 0.125

class DiscoverWSAs(DatagramProtocol):
    def startProtocol(self):
        import socket
        self.transport.socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if platform.system() == 'Windows':
            destinations = get_broadcast_addresses()
        else:
            destinations = ['<broadcast>']
        for d in destinations:
            self.transport.socket.sendto(DISCOVERY_QUERY,
                (d, DISCOVERY_UDP_PORT))

    def datagramReceived(self, data, (host, port)):
        model, serial, firmware = parse_discovery_response(data)
        print model, serial, firmware, 'at', host

reactor.listenUDP(0, DiscoverWSAs())
reactor.callLater(WAIT_TIME, reactor.stop)
reactor.run()
