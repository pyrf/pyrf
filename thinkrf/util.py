
def read_data_and_reflevel(dut, points=1024):
    """
    Wait for and capture a data packet and a reference level packet.

    :returns: (data_pkt, reflevel_pkt)
    """
    # capture 1 packet
    dut.capture(points, 1)

    reference_pkt = None
    # read until I get 1 data packet
    while not dut.eof():
        pkt = dut.read()

        if pkt.is_data_packet():
            break

        if 'reflevel' in pkt.fields:
            reference_pkt = pkt

    return pkt, reference_pkt


def socketread(socket, count, flags = None):
    """
    Retry socket read until count data received,
    like reading from a file.
    """
    if not flags:
        flags = 0
    data = socket.recv(count, flags)
    datalen = len(data)

    if datalen == 0:
        return False

    while datalen < count:
        data = data + socket.recv(count - datalen)
        datalen = len(data)

    return data
