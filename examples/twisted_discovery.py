from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
import struct

WAIT_TIME = 0.125

class DiscoverWSAs(DatagramProtocol):
    SERVERPORT = 18331
    DISCOVERY_RESPONSE_FORMAT = '>LL20sLL'

    def startProtocol(self):
        import socket
        self.transport.socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.transport.socket.sendto("Hello WSA",
            ('<broadcast>', self.SERVERPORT))

    def datagramReceived(self, data, (host, port)):
        resp = struct.unpack(self.DISCOVERY_RESPONSE_FORMAT, data)
        print "WSA4000" if resp[3] == 0 else "WSA5000",
        print resp[2].split('\0',1)[0], "at", host

reactor.listenUDP(0, DiscoverWSAs())
reactor.callLater(WAIT_TIME, reactor.stop)
reactor.run()
