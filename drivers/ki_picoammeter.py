#
# @file ki_picoammeter.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Driver for the KI Picoammeter.
# @version See Git tags for version information.
# @date 2022.08.18
# 
# @copyright Copyright (c) 2022
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#

# from io import TextIOWrapper
import sys
# import glob
from time import sleep
from utilities import ports_finder
from utilities import safe_serial
from utilities import log
import weakref

class KI_Picoammeter:
    def __init__(self, samples: int, man_port: str = None):
        """ KI_Picoammeter constructor.

        Args:
            samples (int): The number of samples to average together to form one output value.
            man_port (str, optional): Overrides the automatically selected port with this one. Defaults to None.

        Raises:
            RuntimeError: Raised if the KI 6485 could not be found.
        """

        # Default values for SafeSerial port.
        self.s = None
        self.found = False
        self.port = -1

        # Connect and initialize communication.
        for port in ports_finder.find_serial_ports():
            if man_port is not None:
                # If `man_port` is defined, only connect on that port. Otherwise, try each available.
                if port != man_port:
                    continue
            
            # Get a SafeSerial connection on the port.
            s = safe_serial.SafeSerial(port, 9600, timeout=1)
            try:
                weakref.finalize(s, safe_serial.safe_close, s)
            except Exception:
                log.error('Could not finalize SafeSerial connection.')

            log.info('Beginning search for Keithley Model 6485...')
            log.info('Trying port %s.'%(port))
            
            # Ask the device on this port for identification.
            s.write(b'*RST\r')
            sleep(0.5)
            s.write(b'*IDN?\r')
            buf = s.read(128).decode('utf-8').rstrip()
            log.debug(buf)

            # Report success and break loop if we have found the KI 6485. Otherwise,
            # continue searching ports.
            if 'KEITHLEY INSTRUMENTS INC.,MODEL 6485' in buf:
                log.info("Keithley Model 6485 found.")
                self.found = True
                self.port = port
                self.s = s
                break
            else:
                log.error("Keithley Model 6485 not found.")
                s.close()

        # Raise exception if KI 6485 not found.
        if self.found == False:
            raise RuntimeError('Could not find Keithley Model 6485!')
        
        # Log which port is being used.
        log.debug('Using port %s.'%(self.port))

        # Set up and start up command sequence for the KI 6485.
        self.s.write(b'SYST:ZCH ON\r')
        sleep(0.1)

        self.s.write(b'RANG 2e-9\r')
        sleep(0.1)

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
        # self.s.write(b'AVER:COUN %d\r'%(self.samples)) # enable averaging
        self.set_samples(samples)

        log.debug('Init complete')

    def set_samples(self, samples: int):
        """ Updates the number of samples the KI 6485 averages together per output value.

        Args:
            samples (int): Number of samples to average.
        """

        if samples < 2:
            samples = 2
        elif samples > 20:
            samples = 20

        self.samples = samples

        self.s.write(b'AVER:COUN %d\r'%(self.samples)) # enable averaging

    def detect(self):
        """ Requests a detector sample from the device.

        Returns:
            _type_: The detector's output value.
        """

        num_read_err_flag = False
        retry_num = 10
        words = None
        while num_read_err_flag and (retry_num > 0):
            num_read_err_flag = False
            retry_num -= 1

            out = ''
            self.s.write(b'READ?\r')
            retry_ser = 10
            while retry_ser:
                buf = self.s.read(128).decode('utf-8').rstrip()
                if len(buf):
                    break
                retry_ser -= 1
            if not retry_ser and len(buf) == 0:
                return out
            out = buf
            spbuf = buf.split(',')
            # try:
            #     if int(float(spbuf[2])) != 2:
            #         log.error("ERROR #%d"%(int(float(spbuf[2]))))
            # except Exception:
            #     log.error('Error: %s invalid output'%(buf))

            # OK:
            # -5.758246E-07A,+2.645176E+03,+2.000000E+00\r
            # Not OK:
            # -2.158728E-06A,+2.647697
            # Not OK (fatal):
            # E+03,+2.000000E+00\r-5.428587E-06A,+2.648818E+03,+2.000000E+00\r

            words = buf.split(',')
            if len(words) != 3:
                log.warn('Error: The detector output an incorrect number of words (', len(words), ', expected 3). The output was:', buf)
                num_read_err_flag = True
            else:
                try:
                    mes = float(words[0][:-1]) # skips the A (unit suffix)
                except Exception as e:
                    log.warn('Error: Could not convert the detector output to a float. The output was:', buf)
                    log.warn('num_read_err_flag:', num_read_err_flag, '; retry_num:', retry_num)
                    num_read_err_flag = True

        if num_read_err_flag:
            err_val = -999.0
            log.error('ERROR: Failed to get a proper value from the detector. Substituting %d for the value. This should never happen, and indicates a significant failure of detector-program communications. Please send the log file to the developer immediately.'%(err_val))
            return err_val

        mes = float(words[0][:-1]) # skips the A (unit suffix)
        # err = int(float(words[2])) # skip timestamp

        mes *= 1e12 # Converts from A to pA

        return mes

    def __del__(self):
        """ KI6485 destructor.
        """

        if self.s is not None:
            self.s.close()

    def short_name(self):
        """ Returns the short name of the device.

        Returns:
            str: The short name.
        """

        return 'KI6485'

    def long_name(self):
        """ Returns the full name of the device.

        Returns:
            str: The full name.
        """
        
        return 'Keithley 6485 Picoammeter'

class KI_Picoammeter_Dummy:
    def __init__(self, samples: int):
        # if samples < 2:
        #     samples = 2
        # elif samples > 20:
        #     samples = 20
        self.set_samples(samples)

        # self.samples = samples
        self.s = None
        self.found = False
        self.port = -1

        log.debug("Picodummy; no port search necessary.")

        log.debug('Using port %s.'%(self.port))

        log.debug('Init complete')


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

    def __del__(self):
        pass

    def short_name(self):
        return 'KI6485'

    def long_name(self):
        return 'Keithley 6485 Picoammeter'

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