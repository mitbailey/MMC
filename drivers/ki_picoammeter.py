from io import TextIOWrapper
import sys
import glob
import serial
from time import sleep
from utilities import ports_finder

class KI_Picoammeter:
    def __init__(self, samples: int, man_port: str = None):
        if samples < 2:
            samples = 2
        if samples > 20:
            samples = 20
        self.samples = samples
        self.s = None
        self.found = False
        self.port = -1
        for port in ports_finder.find_serial_ports():
            if man_port is not None:
                if port != man_port:
                    continue

            s = serial.Serial(port, 9600, timeout=1)
            print('Beginning search for Keithley Model 6485...')
            print('Trying port %s.'%(port))
            s.write(b'*RST\r')
            sleep(0.5)
            s.write(b'*IDN?\r')
            buf = s.read(128).decode('utf-8').rstrip()
            print(buf)

            if 'KEITHLEY INSTRUMENTS INC.,MODEL 6485' in buf:
                print("Keithley Model 6485 found.")
                self.found = True
                self.port = port
                self.s = s
            else:
                # print("Keithley Model 6485 not found.")
                s.close()

        if self.found == False:
            raise RuntimeError('Could not find Keithley Model 6485!')
        print('Using port %s.'%(self.port))

        self.s.write(b'SYST:ZCH ON\r')
        sleep(0.1)
        # buf = s.read(128).decode('utf-8').rstrip()
        # print('SYST:ZCH ON: %s'%(buf))

        self.s.write(b'RANG 2e-9\r')
        sleep(0.1)
        # buf = s.read(128).decode('utf-8').rstrip()

        self.s.write(b'INIT\r')
        sleep(0.1)

        self.s.write(b'SYST:ZCOR:ACQ\r') # acquire zero current
        sleep(0.1)

        self.s.write(b'SYST:ZCOR ON\r') # perform zero correction
        sleep(0.1)

        self.s.write(b'RANG:AUTO ON\r') # enable auto range
        sleep(0.1)

        self.s.write(b'SYST:ZCH OFF\r') # disable zero check
        sleep(0.1)

        self.s.write(b'SYST:ZCOR OFF\r') # disable zero correction
        sleep(0.1)

        self.s.write(b'AVER ON\r')
        self.s.write(b'AVER:TCON REP\r')
        self.s.write(b'AVER:COUN %d\r'%(self.samples)) # enable averaging
        print('Init complete')

    def pinger(self):
        self.s.write(b'*IDN?\r')

    def set_samples(self, samples: int):
        if samples < 2:
            samples = 2
        if samples > 20:
            samples = 20
        self.samples = samples
        self.s.write(b'AVER:COUN %d\r'%(self.samples)) # enable averaging

    def detect(self):
        out = ''
        self.s.write(b'READ?\r')
        retry = 10
        while retry:
            buf = self.s.read(128).decode('utf-8').rstrip()
            if len(buf):
                break
            retry -= 1
        if not retry and len(buf) == 0:
            return out
        out = buf
        spbuf = buf.split(',')
        try:
            if int(float(spbuf[2])) != 2:
                print("ERROR #%d"%(int(float(spbuf[2]))))
        except Exception:
            print('Error: %s invalid output'%(buf))
        return out

    def __del__(self):
        if self.s is not None:
            self.s.close()

    def short_name(self):
        return 'KI6485'

    def long_name(self):
        return 'Keithley 6485 Picoammeter'

class KI_Picoammeter_Dummy:
    def __init__(self, samples: int):
        if samples < 2:
            samples = 2
        if samples > 20:
            samples = 20
        self.samples = samples
        self.s = None
        self.found = False
        self.port = -1
        # for port in serial_ports():
        #     s = serial.Serial(port, 9600, timeout=1)
        #     print('Beginning search for Keithley Model 6485...')
        #     print('Trying port %s.'%(port))
        #     s.write(b'*RST\r')
        #     sleep(0.5)
        #     s.write(b'*IDN?\r')
        #     buf = s.read(128).decode('utf-8').rstrip()
        #     print(buf)

        #     if 'KEITHLEY INSTRUMENTS INC.,MODEL 6485' in buf:
        #         print("Keithley Model 6485 found.")
        #         self.found = True
        #         self.port = port
        #         self.s = s
        #     else:
        #         # print("Keithley Model 6485 not found.")
        #         s.close()
        print("Picodummy; no port search necessary.")

        # if self.found == False:
        #     raise RuntimeError('Could not find Keithley Model 6485!')
        print('Using port %s.'%(self.port))

        print('Init complete')


    def set_samples(self, samples: int):
        if samples < 2:
            samples = 2
        if samples > 20:
            samples = 20
        self.samples = samples
    def detect(self):
        import numpy as np
        out = np.random.random(2)
        return '%eA,%e,0'%(out[0], out[1])
        # self.s.write(b'READ?\r')
        # retry = 10
        # while retry:
        #     buf = self.s.read(128).decode('utf-8').rstrip()
        #     if len(buf):
        #         break
        #     retry -= 1
        # if not retry and len(buf) == 0:
        #     return out
        # out = buf
        # spbuf = buf.split(',')
        # try:
        #     if int(float(spbuf[2])) != 2:
        #         print("ERROR #%d"%(int(float(spbuf[2]))))
        # except Exception:
        #     print('Error: %s invalid output'%(buf))
        return out

    def __del__(self):
        pass
        # if self.s is not None:
            # self.s.close()

    def short_name(self):
        return 'KI6485DUM'

    def long_name(self):
        return 'Keithley 6485 Picoammeter Dummy'

# test code

if __name__ == '__main__':
    import sys
    import signal

    done = False

    def signal_handler(sig, frame):
        global done
        print('You pressed Ctrl+C!')
        done = True

    signal.signal(signal.SIGINT, signal_handler)

    pa = KI_Picoammeter(3)
    while not done:
        print(pa.detect())

    sys.exit(0)


"""
SYST:ZCH ON   ' Enable zero check.
RANG 2e-9     ' Select the 2nA range.
INIT          ' Trigger reading to be used as zero correction
SYST:ZCOR:ACQ ' Use last reading taken as zero correct value
SYST:ZCOR ON  ' Perform zero correction.
RANG:AUTO ON  ' Enable auto range.
SYST:ZCH OFF  ' Disable zero check.
READ?         ' Trigger and return one reading.



Ranges: 2nA 20nA 200nA     2uA 20uA 200uA     2mA 20mA, with 5% overrange. OVERFLOW on overflow.

Filters:
MED <ON/OFF> -> median filter enable/disable
MED:RANK <N> -> median filter rank 1 to 5

AVER <ON/OFF> -> average filter
AVER:TCON <name> -> select filter control MOVing or REPeat
AVER:COUN <n> -> filter count: 2 to 100


Signal commands:
CONF[:<function>] -> places model 6485/6487 in a oneshot measurement mode. <function> = CURR[:DC]
CONF? -> queries the selected function. Returns 'CURR'
FETC? -> Requests the latest readings
READ? -> Performs an  INIT and a :FETC? (equivalent to INIT:FETC?)
MEAS[:<function>]? -> Performs a CONF:<function> and a :READ? (equivalent to CONF:CURR[:DC]:FETC?)

CAL -> Instrument calibration
STAT -> Instrument status
TRIG -> Instrument triggering
TRAC -> Buffer operation and data
SYST -> Zero check, correct, line freq, error message
SENS -> Current measurements and associated modes
FORM -> format of returned remote data


SCPI command words are not case sensitive, can be sent in long or short form. Multiple command messages can be sent at once as long as they are separated by semicolons (;)
The query command requests the presently programmed status. It is identified by the question mark (?) at the end of the fundamental form of the command. Most commands have
a query form.

Each program message must be terminated with an LF (\n), EOI (end of identify), or an LF + EOI. Each response is terminated with an LF and EOI.

Parameter types:
<b> -> Boolean, 0 or OFF, 1 or ON
<name> -> parameter name from listed group
<NRf> -> Numeric representation, 8, 23.6, 2.3e6 etc
<NDN> -> non-decimal numeric. A unique header identifies the format: #B for binary, #H for hex and #Q for octal
<n> -> NUmeric value - can consist of an NRf number or one of the following name parameters: DEFault, MINimum, or MAXimum. When the DEFault parameter is used, the instrument
is programmed to the *RST default value. When the MIN parameter is used, the instrument is programmed to the lowest allowable value, etc.
"""