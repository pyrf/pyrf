
def read_data_and_context(dut, points=1024):
    """
    Wait for and capture a data packet and collect preceeding context packets.

    :returns: (data_pkt, context_values)

    Where context_values is a dict of {field_name: value} items from
    all the context packets received.
    """
    # capture 1 packet
    dut.capture(points, 1)

    context_values = {}
    # read until I get 1 data packet
    while not dut.eof():
        pkt = dut.read()

        if pkt.is_data_packet():
            break

        context_values.update(pkt.fields)

    return pkt, context_values

# avoid breaking pyrf 0.2.x examples:
read_data_and_reflevel = read_data_and_context

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
