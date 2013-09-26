#!/usr/bin/python
import socket
import struct
import select
import platform


SERVERPORT = 18331
WSA_VERSION_RESPONSE_FORMAT = '>II'

WSA5000_DISCOVERY_RESPONSE_FORMAT = WSA_VERSION_RESPONSE_FORMAT +'52s'
WSA4000_DISCOVERY_RESPONSE_FORMAT = WSA_VERSION_RESPONSE_FORMAT + '28s'

WSA4000_DISCOVERY_VERSION = 1
WSA5000_DISCOVERY_VERSION = 2

WAIT_TIME = 0.125

WSA_QUERY_CODE = 0x93315555
WSA_QUERY_VERSION = 2
DISCOVERY_QUERY_FORMAT =  '>LL'

cs = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
cs.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
cs.setblocking(0)

if platform.system() == 'Windows':
    import _windows_networks
    destinations = _windows_networks.get_broadcast_addresses()
else:
    destinations = ['<broadcast>']

for d in destinations:
    # send query command to WSA
    query_struct = struct.pack(DISCOVERY_QUERY_FORMAT , WSA_QUERY_CODE, WSA_QUERY_VERSION)
    cs.sendto(query_struct, (d, SERVERPORT))
    
while True:
    ready, _, _ = select.select([cs], [], [], WAIT_TIME)
    if not ready:
        break
    data, (host, port) = cs.recvfrom(1024)
    
    # extract the version from the WSA
    version = struct.unpack(WSA_VERSION_RESPONSE_FORMAT, data[0:8])[1]
    
    # determine if the device is a WSA4000
    if version == WSA4000_DISCOVERY_VERSION :     
        resp = struct.unpack(WSA4000_DISCOVERY_RESPONSE_FORMAT, data)
        print 'WSA4000', resp[2].split('\0',1)[0], "at", host
    
    # determine if the device is a WSA5000
    elif version == WSA5000_DISCOVERY_VERSION:

        resp = struct.unpack(WSA5000_DISCOVERY_RESPONSE_FORMAT, data)
        print resp[2][0:11], resp[2][16:25].rstrip('\x00'),"at", host
