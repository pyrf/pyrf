#!/usr/bin/python
 
# Based on getifaddrs.py from pydlnadms [http://code.google.com/p/pydlnadms/].
# Only tested on Linux!

try:
    from socket import AF_INET, AF_INET6, inet_ntop, inet_pton
except ImportError:
    pass  # expected to fail on windows
from ctypes import (
    Structure, Union, POINTER,
    pointer, get_errno, cast,
    c_ushort, c_byte, c_void_p, c_char_p, c_uint, c_int, c_uint16, c_uint32
)
import ctypes.util
import ctypes
from struct import pack, unpack
 
class struct_sockaddr(Structure):
    _fields_ = [
    ('sa_family', c_ushort),
    ('sa_data', c_byte * 14),]
 
class struct_sockaddr_in(Structure):
    _fields_ = [
    ('sin_family', c_ushort),
    ('sin_port', c_uint16),
    ('sin_addr', c_byte * 4)]
 
class struct_sockaddr_in6(Structure):
    _fields_ = [
    ('sin6_family', c_ushort),
    ('sin6_port', c_uint16),
    ('sin6_flowinfo', c_uint32),
    ('sin6_addr', c_byte * 16),
    ('sin6_scope_id', c_uint32)]
 
class union_ifa_ifu(Union):
    _fields_ = [
    ('ifu_broadaddr', POINTER(struct_sockaddr)),
    ('ifu_dstaddr', POINTER(struct_sockaddr)),]
 
class struct_ifaddrs(Structure):
    pass
struct_ifaddrs._fields_ = [
    ('ifa_next', POINTER(struct_ifaddrs)),
    ('ifa_name', c_char_p),
    ('ifa_flags', c_uint),
    ('ifa_addr', POINTER(struct_sockaddr)),
    ('ifa_netmask', POINTER(struct_sockaddr)),
    ('ifa_ifu', union_ifa_ifu),
    ('ifa_data', c_void_p),]
 
libc = ctypes.CDLL(ctypes.util.find_library('c'))
 
def ifap_iter(ifap):
    ifa = ifap.contents
    while True:
        yield ifa
        if not ifa.ifa_next:
            break
        ifa = ifa.ifa_next.contents
 
def getfamaddr(sa):
    family = sa.sa_family
    addr = None
    if family == AF_INET:
        sa = cast(pointer(sa), POINTER(struct_sockaddr_in)).contents
        addr = inet_ntop(family, sa.sin_addr)
    elif family == AF_INET6:
        sa = cast(pointer(sa), POINTER(struct_sockaddr_in6)).contents
        addr = inet_ntop(family, sa.sin6_addr)
    return family, addr

def getbcaddr(addr, mask):

    x = unpack('I', inet_pton(AF_INET, addr))
    sa = x[0] & 0xffffffff
    x = unpack('I', inet_pton(AF_INET, mask))
    nm = x[0] & 0xffffffff
    bc = (sa | ~nm) & 0xffffffff
    #print 'sa=%08x nm=%08x bc=%08x' % (sa, nm, bc)
    bcaddr = pack('I', bc)
    return inet_ntop(AF_INET, bcaddr)
  
class NetworkInterface(object):
    def __init__(self, name):
        self.name = name
        self.index = libc.if_nametoindex(name)
        self.addresses = {}
        self.netmasks = {}
        self.bcaddress = '0.0.0.0'
 
    def __str__(self):
        return "%s [index=%d, IPv4=%s/%s %s, IPv6=%s/%s]" % (
            self.name, self.index,
            self.addresses.get(AF_INET),
            self.netmasks.get(AF_INET),
            self.bcaddress,
            self.addresses.get(AF_INET6),
            self.netmasks.get(AF_INET6))
 
def get_network_list():
    ifap = POINTER(struct_ifaddrs)()
    result = libc.getifaddrs(pointer(ifap))
    if result != 0:
        raise OSError(get_errno())
    del result
    try:
        retval = {}
        for ifa in ifap_iter(ifap):
            name = ifa.ifa_name
            i = retval.get(name)
            if not i:
                i = retval[name] = NetworkInterface(name)
            family, addr = getfamaddr(ifa.ifa_addr.contents)
            if addr:
                i.addresses[family] = addr
            if ifa.ifa_netmask:
                family, netmask = getfamaddr(ifa.ifa_netmask.contents)
                i.netmasks[family] = netmask
                if family == AF_INET:
                    i.bcaddress = getbcaddr(addr, netmask)
        return retval
    finally:
        libc.freeifaddrs(ifap)

def get_network_interfaces():
    retval = get_network_list()
    return retval.values()

def get_broadcast_addresses():
    retval = []
    list = get_network_list()
    for i in list:
        if list[i].addresses.get(AF_INET) != '127.0.0.1':
            retval.append(list[i].bcaddress)
    return retval

if __name__ == '__main__':
    print [str(ni) for ni in get_network_interfaces()]
