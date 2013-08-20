#!/usr/bin/python
import socket
import struct
import signal

SERVERPORT = 18331
DISCOVERY_RESPONSE_FORMAT = '>LL20sLL'
WAIT_TIME = 1

cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

cs.sendto('Hello WSA', ('<broadcast>', SERVERPORT))

signal.alarm(WAIT_TIME) # toy example, alarm() is not for real code
while True:
    data, (host, port) = cs.recvfrom(1024)
    resp = struct.unpack(DISCOVERY_RESPONSE_FORMAT, data)
    print "WSA4000" if resp[3] == 0 else "WSA5000",
    print resp[2].split('\0',1)[0], "at", host
