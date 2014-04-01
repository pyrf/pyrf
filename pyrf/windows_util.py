import subprocess
def get_broadcast_addresses():
    """
    Windows does not support broadcast to 255.255.255.255 so we need
    to enumerate the networks and generate separate network
    broadcast addresses instead.
    """

    # WSAIoctl is hard to access in python, so we do this the dirty way
    s = subprocess.Popen('ipconfig', stdout=subprocess.PIPE)

    # XXX: IPv4 only for now
    out = []
    addr = None
    for ln in s.stdout:
        ln = ln.strip()
        if not ln:
            addr = None
            continue
        if 'Address' in ln:
            addr = ln.split(':', 1)[-1].strip()
            continue
        if 'Mask' in ln:
            mask = ln.split(':', 1)[-1].strip()
            out.append('.'.join(
                str(int(a) | (int(m) ^ 255)) for a, m in zip(
                    addr.split('.'), mask.split('.'))))
    return out
