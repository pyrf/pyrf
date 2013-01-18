
PyRF
====

This library currently supports development for the `WSA4000 Platform`_,
but may support additional hardware in the future.

.. _WSA4000 Platform: http://www.thinkrf.com/products.html

Documentation
-------------

* `Documentation for this API <http://pyrf.rtfd.org>`_
* `WSA4000 Documentation <http://www.thinkrf.com/resources>`_


Cross-platform GUI Included
---------------------------

.. image:: http://pyrf.readthedocs.org/en/latest/_images/wsa4000demo.png

Example Code
------------

::

    from pyrf.devices.thinkrf import WSA4000

    # connect to wsa
    dut = WSA4000()
    dut.connect("10.126.110.103")

    # setup test conditions
    dut.request_read_perm()
    dut.ifgain(0)
    dut.freq(2450e6)
    dut.gain('low')
    dut.fshift(0)
    dut.decimation(0)

    # capture 1 packet with 1024 samples
    dut.capture(1024, 1)

    # skip the context packets
    while not dut.eof():
        pkt = dut.read()

        if pkt.is_data_packet():
            break

    # print I/Q data
    for i, q in pkt.data:
        print "%d,%d" % (i, q)
