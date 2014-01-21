
def read_data_and_context(dut, points=1024):
    """
    Initiate capture of one data packet, wait for and return data packet
    and collect preceeding context packets.

    :returns: (data_pkt, context_values)

    Where context_values is a dict of {field_name: value} items from
    all the context packets received.
    """
    # capture 1 packet
    dut.capture(points, 1)

    return collect_data_and_context(dut)

def collect_data_and_context(dut):
    """
    Wait for and return data packet and collect preceeding context packets.
    """
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

