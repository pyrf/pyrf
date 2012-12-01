from numpy import fft, abs, log10
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
    cfft = fft.fft(cdata)
    cfft = fft.fftshift(cfft)

    # compute power
    return log10(abs(cfft)) * 20
