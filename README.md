Documentation
=============
Module is documented with Doxygen.  Run to generate latex or html documentation.

    # doxygen

Example:
--------

```python
from WSA4000 import WSA4000

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

# capture 1 packet
dut.capture(1024, 1)

# read until I get 1 data packet
while not dut.eof():
    pkt = dut.read()

    if pkt.is_data_packet():
        break

# print I/Q data into i and q
for t in pkt.data:
    print "%d,%d" % (t[0], t[1])
```
