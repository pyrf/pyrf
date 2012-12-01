import numpy
import math

def read_power_data(dut):
    # capture 1 packet
    dut.capture(1024, 1)

    # read until I get 1 data packet
    while not dut.eof():
        pkt = dut.read()

        if pkt.is_data_packet():
            break

    # seperate data into i and q
    cdata = [complex(i, q) for i, q in pkt.data]

    # compute the fft of the complex data
    cfft = numpy.fft.fft(cdata)
    cfft = numpy.fft.fftshift(cfft)

    # compute power
    return numpy.log10(numpy.abs(cfft)) * 20
