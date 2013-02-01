from twisted.internet import defer

@defer.inlineCallbacks
def read_data_and_context(dut, points=1024):
    """
    Wait for and capture a data packet and collect preceeding context packets.

    :returns: (data_pkt, context_values)

    Where context_values is a dict of {field_name: value} items from
    all the context packets received.
    """
    # capture 1 packet
    yield dut.capture(points, 1)

    context_values = {}
    # read until I get 1 data packet
    while not dut.eof():
        pkt = yield dut.read()

        if pkt.is_data_packet():
            break

        context_values.update(pkt.fields)

    defer.returnValue((pkt, context_values))

