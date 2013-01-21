from twisted.internet import defer

@defer.inlineCallbacks
def read_data_and_reflevel(dut, points=1024):
    """
    Wait for and capture a data packet and a reference level packet.

    :returns: (data_pkt, reflevel_pkt)
    """
    # capture 1 packet
    yield dut.capture(points, 1)

    reference_pkt = None
    # read until I get 1 data packet
    while not dut.eof():
        pkt = yield dut.read()

        if pkt.is_data_packet():
            break

        if 'reflevel' in pkt.fields:
            reference_pkt = pkt

    defer.returnValue((pkt, reference_pkt))

