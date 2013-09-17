#!/usr/bin/python

from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
import struct
import platform

WAIT_TIME = 0.125

class DiscoverWSAs(DatagramProtocol):
    SERVERPORT = 18331
    DISCOVERY_RESPONSE_FORMAT = '>LL20sLL'

    def startProtocol(self):
        import socket
        self.transport.socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        if platform.system() == 'Windows':
            import _windows_networks
            destinations = _windows_networks.get_broadcast_addresses()
        else:
            destinations = ['<broadcast>']
        for d in destinations:
            self.transport.socket.sendto("Hello WSA",
                (d, self.SERVERPORT))

    def datagramReceived(self, data, (host, port)):
        resp = struct.unpack(self.DISCOVERY_RESPONSE_FORMAT, data)
        print "WSA4000" if resp[3] == 0 else "WSA5000",
        print resp[2].split('\0',1)[0], "at", host

reactor.listenUDP(0, DiscoverWSAs())
reactor.callLater(WAIT_TIME, reactor.stop)
reactor.run()
