#
# @file sr810.py
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

# NOTES ABOUT LOCKIN
# INTERFACE >>> Setup
# GPIB/RS232:   RS232
# ADDRESS:      12
# BAUD:         9600
# PARITY:       None

from io import TextIOWrapper
import sys
import glob
from time import sleep
from utilities import ports_finder
from utilities import safe_serial
from utilities import log

class SR810:
    def __init__(self, man_port: str = None):
        # if samples < 2:
        #     samples = 2
        # if samples > 20:
        #     samples = 20
        # self.samples = samples
        self.s = None
        self.found = False
        self.port = -1
        for port in ports_finder.find_serial_ports():
            if man_port is not None:
                if port != man_port:
                    continue

            s = safe_serial.SafeSerial(port, 9600, timeout=1)
            log.info('Beginning search for SR810...')
            log.info('Trying port %s.'%(port))
            s.write(b'*RST')
            sleep(0.5)
            s.write(b'*IDN?')
            buf = s.read(128).decode('utf-8').rstrip()
            log.debug(buf)

            if 'Stanford_Research_Systems,SR810,' in buf:
                log.info("SR810 found.")
                self.found = True
                self.port = port
                self.s = s
            else:
                log.error("SR810 not found.")
                s.close()

        if self.found == False:
            raise RuntimeError('Could not find SR810!')
        log.debug('Using port %s.'%(self.port))

        # Set the system to LOCAL mode. This allows both commands and front-panel buttons to control the instrument.
        self.s.write(b'LOCL 0')
        sleep(0.1)

        self.s.write(b'LOCL?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('SR810 is in LOCAL mode.')
        else:
            log.warn('SR810 is not in LOCAL mode!')

        # Set the time constant to 300ms.
        self.s.write(b'OFLT 9')
        sleep(0.1)

        self.s.write(b'OFLT?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '9'):
            log.info('Time constant is 300ms.')
        else:
            log.warn('Time constant is not 300ms!')

        # Set the low pass filter slope.
        self.s.write(b'OFSL 1')
        sleep(0.1)

        self.s.write(b'OFSL?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '1'):
            log.info('Low pass filter slope is 12dB/octave.')
        else:
            log.warn('Low pass filter slope is not 12dB/octave!')

        # Set the sync to 200 Hz.
        self.s.write(b'SYNC 1')
        sleep(0.1)

        self.s.write(b'SYNC?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '1'):
            log.info('Sync is 200 Hz.')
        else:
            log.warn('Sync is not 200 Hz!')

        # Signal input to A.
        self.s.write(b'ISRC 0')
        sleep(0.1)

        self.s.write(b'ISRC?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('Signal input is A.')
        else:
            log.warn('Signal input is not A!')

        # Set the input coupling to AC.
        self.s.write(b'ICPL 0')
        sleep(0.1)

        self.s.write(b'ICPL?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('Input coupling is AC.')
        else:
            log.warn('Input coupling is not AC!')

        # Ground / float.
        self.s.write(b'IGND 0')
        sleep(0.1)

        self.s.write(b'IGND?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('Ground is float.')
        else:
            log.warn('Ground is not float!')

        # Set auto sensitivity.
        # This command takes forever to complete, so we have to wait on *STB? 1 to be 1. 
        # TODO: Comment out AGAN once we setup an option for the user to do it from within the GUI. For now, we can leave it like so.
        self.s.write(b'AGAN')
        sleep(0.1)

        rdy = False
        while (not rdy):
            self.s.write(b'*STB? 1')
            buf = self.s.read(128).decode('utf-8').rstrip()
            if (buf == '1'):
                rdy = True
            else:
                sleep(0.1)

        # Reserve HIGH to Vuvas.
        self.s.write(b'RMOD 1')
        sleep(0.1)

        self.s.write(b'RMOD?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '1'):
            log.info('Reserve is HIGH.')
        else:
            log.warn('Reserve is not HIGH!')

        # Set both LINE and x2 LINE notch filters ON.
        self.s.write(b'ILIN 3')
        sleep(0.1)

        self.s.write(b'ILIN?')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '1'):
            log.info('Notch filters both on.')
        else:
            log.warn('Notch filter not both on!')

        # Turn both filter ON.
        # ??? What does this mean
            
        # Set trigger to pos edge.
        # No command seems to exist.

        # Do not set phasing to auto.
        # Ok.

        log.info('Init complete')

    def detect(self):
        self.s.write(b'OUTP ? 1')
        X = self.s.read(128).decode('utf-8').rstrip()
        if X == '': X = 0
        self.val_X = float(X)

        return self.val_X

    def __del__(self):
        if self.s is not None:
            self.s.close()

    def short_name(self):
        return 'SR810'

    def long_name(self):
        return 'Stanford Research Systems 810 Lock-In Amplifier'

class SR810_DUMMY:
    def __init__(self, man_port: str = None):
        pass

    def detect(self):
        import numpy as np

        mes = self.prev_mes + np.random.normal(0, 1)
        self.prev_mes = mes

        return mes

    def __del__(self):
        pass

    def short_name(self):
        return 'SR810'

    def long_name(self):
        return 'Stanford Research Systems 810 Lock-In Amplifier'