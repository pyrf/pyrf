Documentation
=============
Module is documented with Doxygen.  Run to generate latex or html documentation.
# doxygen

Example:
--------

```python
from collections import namedtuple
import VRTDataPacket
import VRTContextPacket
import WSA4000
import WSA4000SweepEntry

# connect to wsa
dut = WSA4000.WSA4000()
dut.connect("10.126.110.103")

# setup test conditions
dut.ifgain(0)
dut.freq(2450e6)
dut.gain('low')
dut.fshift(0)
dut.decimation(0)

# capture 1 packet
dut.capture(1024, 1)

# read until I get 1 data packet
count = 0
while not dut.eof():
    pkt = dut.read()

    if pkt.__class__.__name__ == "VRTDataPacket":
        count = count + 1

    if count == 1:
        break

# print I/Q data into i and q
for t in pkt.data:
    print "%d,%d" % (i[0], i[1])
```
