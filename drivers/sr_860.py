#
# @file sr860.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Detector Driver for the SR860 Lock-In Amplifier.
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
import serial
from time import sleep
from utilities import ports_finder
from utilities import safe_serial
from utilities import log

class SR860:
    # def __init__(self, man_port: str = None):
    def __init__(self, port: serial.Serial):
        # if samples < 2:
        #     samples = 2
        # if samples > 20:
        #     samples = 20
        # self.samples = samples
        self.s = None
        self.found = False
        # self.port = -1
        # for port in ports_finder.find_serial_ports():
        #     if man_port is not None:
        #         if port != man_port:
        #             continue

        # CRITICAL!!!!
        # This needs to not clog up all the ports during a search. Just use the one the user gives it....

        if port is None:
            log.error('Port is none type.')
            raise RuntimeError('Port is none type.')

        log.info('Attempting to connect to LockIn 860 on port %s.'%(port))

        ser_ports = ports_finder.find_serial_ports()
        if port not in ser_ports:
            log.error('Port not valid. Is another program using the port?')
            log.error('%s\nnot found in\n%s'%(port, ser_ports))
            raise RuntimeError('Port not valid. Is another program using the port?')

        s = safe_serial.SafeSerial(port, 9600, timeout=0.25)

        log.info('Beginning search for SR860...')
        log.info('Trying port %s.'%(port))
        # s.write(b'*RST\n')
        # sleep(0.5)

        s.write(b'*TST?\n')
        buf = s.read(128).decode('utf-8').rstrip()
        log.debug(buf)

        s.write(b'*IDN?\n')
        buf = s.read(128).decode('utf-8').rstrip()
        log.debug(buf)

        sleep(1)

        s.write(b'*IDN?\n')
        buf = s.read(128).decode('utf-8').rstrip()
        log.debug(buf)

        # if 'Stanford_Research_Systems,SR860,' in buf:
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
        self.s.write(b'LOCL 0\n')
        sleep(0.1)

        self.s.write(b'LOCL?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('SR860 is in LOCAL mode.')
        else:
            log.warn('SR860 is not in LOCAL mode!')

        self.s.write(b'ERRE 255\n')
        sleep(0.1)

        self.s.write(b'ERRE?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '255'):
            log.info('Error Enable set to 255.')
        else:
            log.warn('Error Enable not set to 255!')

        # Set the time constant to 300ms.
        self.s.write(b'OFLT 9\n')
        sleep(0.1)

        self.s.write(b'OFLT?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '9'):
            log.info('Time constant is 300ms.')
        else:
            log.warn('Time constant is not 300ms!')

        # Set the low pass filter slope.
        self.s.write(b'OFSL 1\n')
        sleep(0.1)

        self.s.write(b'OFSL?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '1'):
            log.info('Low pass filter slope is 12dB/octave.')
        else:
            log.warn('Low pass filter slope is not 12dB/octave!')

        # Set the sync to 200 Hz.
        self.s.write(b'SYNC 1\n')
        sleep(0.1)

        self.s.write(b'SYNC?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '1'):
            log.info('Sync is 200 Hz.')
        else:
            log.warn('Sync is not 200 Hz!')

        # Signal input to A.
        self.s.write(b'ISRC 0\n')
        sleep(0.1)

        self.s.write(b'ISRC?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('Signal input is A.')
        else:
            log.warn('Signal input is not A!')

        # Set the input coupling to AC.
        self.s.write(b'ICPL 0\n')
        sleep(0.1)

        self.s.write(b'ICPL?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('Input coupling is AC.')
        else:
            log.warn('Input coupling is not AC!')

        # Ground / float.
        self.s.write(b'IGND 0\n')
        sleep(0.1)

        self.s.write(b'IGND?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('Ground is float.')
        else:
            log.warn('Ground is not float!')

        # There is no auto gain on the SR860!
        # Set auto sensitivity.
        # This command takes forever to complete, so we have to wait on *STB? 1 to be 1. 
        # TODO: Comment out AGAN once we setup an option for the user to do it from within the GUI. For now, we can leave it like so.
        # self.s.write(b'AGAN\n')
        # sleep(0.1)

        # rdy = False
        # while (not rdy):
        #     self.s.write(b'*STB? 1\n')
        #     buf = self.s.read(128).decode('utf-8').rstrip()
        #     if (buf == '1'):
        #         rdy = True
        #     else:
        #         sleep(0.1)

        # Reserve HIGH to Vuvas.
        self.s.write(b'RMOD 1\n')
        sleep(0.1)

        self.s.write(b'RMOD?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '1'):
            log.info('Reserve is HIGH.')
        else:
            log.warn('Reserve is not HIGH!')

        # Not a valid command on SR860.
        # # Set both LINE and x2 LINE notch filters ON.
        # self.s.write(b'ILIN 3\n')
        # sleep(0.1)

        # self.s.write(b'ILIN?\n')
        # buf = self.s.read(128).decode('utf-8').rstrip()
        # if (buf == '1'):
        #     log.info('Notch filters both on.')
        # else:
        #     log.warn('Notch filter not both on!')

        # Turn both filter ON.
        # ??? What does this mean
            
        # Set trigger to pos edge.
        # No command seems to exist.

        # Do not set phasing to auto.

        log.info('Init complete')

        # print('\n\n\n\n\n\n\n\n')
        # sleep(1)
        # exit(0)

    def detect(self):
        # 0 for X, 1 for Y.
        self.s.write(b'OUTP? 0\n')
        X = self.s.read(128).decode('utf-8').rstrip()
        if X == '': X = 0
        self.val_X = float(X)

        self.s.write(b'ERRS?\n')
        buf = self.s.read(128).decode('utf-8').rstrip()
        if (buf == '0'):
            log.info('No errors.')
        else:
            log.warn('Error detected!')
            log.warn('Error: %s'%(buf))

        return self.val_X

    def __del__(self):
        if self.s is not None:
            self.s.close()

    def short_name(self):
        return 'SR860'

    def long_name(self):
        return 'Stanford Research Systems 860 Lock-In Amplifier'

class SR860_DUMMY:
    def __init__(self, man_port: str = None):
        pass

    def detect(self):
        return 3.7*5

    def __del__(self):
        pass

    def short_name(self):
        return 'SR860'

    def long_name(self):
        return 'Stanford Research Systems 860 Lock-In Amplifier'