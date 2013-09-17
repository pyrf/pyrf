#!/usr/bin/python
import socket
import struct
import select

SERVERPORT = 18331
DISCOVERY_RESPONSE_FORMAT = '>LL20sLL'
WAIT_TIME = 0.125

cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
cs.setblocking(0)

cs.sendto('Hello WSA', ('<broadcast>', SERVERPORT))

while True:
    ready, _, _ = select.select([cs], [], [], WAIT_TIME)
    if not ready:
        break
    data, (host, port) = cs.recvfrom(1024)
    resp = struct.unpack(DISCOVERY_RESPONSE_FORMAT, data)
    print "WSA4000" if resp[3] == 0 else "WSA5000",
    print resp[2].split('\0',1)[0], "at", host
