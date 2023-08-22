#
# @file sr860.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Detector Driver for the SR810 Lock-In Amplifier.
# @version See Git tags for version information.
# @date 2023.08.08
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

from io import TextIOWrapper
import sys
import glob
from time import sleep
from utilities import ports_finder
from utilities import safe_serial
from utilities import log

class SR_860:
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

            s = safe_serial.SafeSerial(port, 9600, timeout=1)
            log.info('Beginning search for Keithley Model 6485...')
            log.info('Trying port %s.'%(port))
            s.write(b'*RST\r')
            sleep(0.5)
            s.write(b'*IDN?\r')
            buf = s.read(128).decode('utf-8').rstrip()
            log.debug(buf)

            if 'KEITHLEY INSTRUMENTS INC.,MODEL 6485' in buf:
                log.info("Keithley Model 6485 found.")
                self.found = True
                self.port = port
                self.s = s
            else:
                log.error("Keithley Model 6485 not found.")
                s.close()

        if self.found == False:
            raise RuntimeError('Could not find Keithley Model 6485!')
        log.debug('Using port %s.'%(self.port))

        self.s.write(b'SYST:ZCH ON\r')
        sleep(0.1)

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
        log.debug('Init complete')

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
                log.error("ERROR #%d"%(int(float(spbuf[2]))))
        except Exception:
            log.error('Error: %s invalid output'%(buf))
        return out

    def __del__(self):
        if self.s is not None:
            self.s.close()

    def short_name(self):
        return 'KI6485'

    def long_name(self):
        return 'Keithley 6485 Picoammeter'

class SR_860_DUMMY:
    def __init__(self, samples: int):
        pass

    def set_samples(self, samples: int):
        pass

    def detect(self):
        pass
    def __del__(self):
        pass

    def short_name(self):
        return 'SR860DUM'

    def long_name(self):
        return 'Stanford Research 860 Lock-In Amplifier Dummy'

""" Command Set
"""