#!/usr/bin/python
import socket
import struct
import select
import platform

from pyrf.devices.thinkrf import (DISCOVERY_UDP_PORT, DISCOVERY_QUERY,
    parse_discovery_response)


WAIT_TIME = 0.125

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
    query_struct = DISCOVERY_QUERY
    cs.sendto(query_struct, (d, DISCOVERY_UDP_PORT))

while True:
    ready, _, _ = select.select([cs], [], [], WAIT_TIME)
    if not ready:
        break
    data, (host, port) = cs.recvfrom(1024)

    model, serial, firmware = parse_discovery_response(data)

    print model, serial, firmware, 'at', host
