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
            log.info('Beginning search for SR860...')
            log.info('Trying port %s.'%(port))
            s.write(b'*RST\r')
            sleep(0.5)
            s.write(b'*IDN?\r')
            buf = s.read(128).decode('utf-8').rstrip()
            log.debug(buf)

            if 'Stanford_Research_Systems,SR860,' in buf:
                log.info("SR860 found.")
                self.found = True
                self.port = port
                self.s = s
            else:
                log.error("SR860 not found.")
                s.close()

        if self.found == False:
            raise RuntimeError('Could not find SR860!')
        log.debug('Using port %s.'%(self.port))

        # Set the system to LOCAL mode. This allows both commands and front-panel buttons to control the instrument.
        self.s.write(b'LOCL 0\r')
        sleep(0.1)

        # TODO: Whatever standard settings are desired.
        # TODO: (Maybe) Do we want to check settings? If so, what do we do in an error? Or should we check after this.

        log.debug('Init complete')

    def detect(self):
        pass

    def __del__(self):
        if self.s is not None:
            self.s.close()

    def short_name(self):
        return 'SR860'

    def long_name(self):
        return 'Stanford Research Systems 860 Lock-In Amplifier'

class SR_860_DUMMY:
    def __init__(self, samples: int):
        pass

    def detect(self):
        pass

    def __del__(self):
        pass

    def short_name(self):
        return 'SR860DUM'

    def long_name(self):
        return 'Stanford Research Systems 860 Lock-In Amplifier Dummy'

""" Command Set
"""