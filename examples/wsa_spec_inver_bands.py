from pyrf.devices.thinkrf import WSA
import sys


dut = WSA()
dut.connect(sys.argv[1])
dut.reset()
dut.flush()
dut.request_read_perm()
SAMPLE_SIZE = 1024
FREQ_MIN = "50 MHZ"
FREQ_MAX = "20 GHZ"
STEP = "1 MHZ"
DEBUG = False
dut.scpiset(":SWE:ENTRY:MODE SH")
dut.scpiset(":SWE:ENTRY:FREQ:CENTER "+FREQ_MIN+","+FREQ_MAX)
dut.scpiset(":SWE:LIST:ITER 2")
dut.scpiset(":SWE:ENTRY:FREQ:STEP "+STEP)
dut.scpiset(":SWE:ENTRY:ATT OFF")
dut.scpiset(":SWE:ENTRY:SPP "+str(SAMPLE_SIZE))
dut.scpiset(":sweep:entry:save")
dut.sweep_start()
if DEBUG:
    print dut.rfe_mode()
    print dut.scpiget(":SWE:LIST:STAT?")
    print dut.scpiget("SYST:CAPT:MODE?")
    print dut.scpiget(":SWE:ENTRY:SPP?")
    print dut.scpiget("SYST:ERR?")
i = 50
y = 0
freqHolder = 0
specInvFlag = "False"
oldStartFreq = 50
while not dut.eof():
    pkt = dut.read()
    if pkt.is_data_packet():
        if str(pkt.spec_inv) != str(specInvFlag):
            print str(oldStartFreq) + " -  " + str(i-1) + ":  " + str( not pkt.spec_inv)
            specInvFlag = str(pkt.spec_inv)
            oldStartFreq = i
        i += 1
    else:
        if 'rffreq' in pkt.fields:
            if freqHolder < pkt.fields['rffreq']:
                freqHolder = pkt.fields['rffreq']
            else:
                print str(oldStartFreq) + " -  " + str(i-1) + ":  " + str(specInvFlag)

                i = 0
                y += 1
                freqtest = 0
                if y == 1:
                    break
dut.sweep_stop()   
