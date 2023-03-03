#
# @file mp_789a_4.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Driver for the McPherson Model 789A-4 Scan Controller.
# @version See Git tags for version information.
# @date 2022.11.04
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

import serial
import time
from utilities import ports_finder

# Driver class for the McPherson 789A-4.
# This class is also used by the 792, since the 792 is essentially four 789A-4s addressed separately.

class MP_789A_4:
    def __init__(self, port):
        self.s_name = 'MP789'
        self.l_name = 'McPherson 789A-4'
        self._is_homing = False
        self._moving = False

        self._position = 0

        print('Attempting to connect to McPherson Model 789A-4 Scan Controller on port %s.'%(port))

        if port is None:
            print('Port is none type.')
            raise RuntimeError('Port is none type.')
            

        ser_ports = ports_finder.find_serial_ports()
        if port not in ser_ports:
            print('Port not valid. Is another program using the port?')
            raise RuntimeError('Port not valid. Is another program using the port?')

        self.s = serial.Serial(port, 9600, timeout=1)
        self.s.write(b' \r')
        time.sleep(0.1)
        rx = self.s.read(128)#.decode('utf-8').rstrip()
        print(rx)

        if rx is None or rx == b'':
            raise RuntimeError('Response timed out.')
        elif rx == b' v2.55\r\n#\r\n':
            print('McPherson model 789A-4 Scan Controller found.')
        elif rx == b' #\r\n':
            print('McPherson model 789A-4 Scan Controller already initialized.')
        else:
            raise RuntimeError('Invalid response.')

        if self.s is None:
            raise RuntimeError('self.s is None')

        self.home()

    def home(self)->bool:
        print('Beginning home.')
        self._is_homing = True

        # Enable Home Circuit
        self.s.write(b'A8\r')
        time.sleep(0.1)
        rx = self.s.read(128).decode('utf-8')

        # Check Limit Status
        self.s.write(b']\r')
        time.sleep(0.1)
        rx_raw = self.s.read(128)
        rx = rx_raw.decode('utf-8')
        # rx = self.s.read(128).decode('utf-8')

        print('RECEIVED (raw):', rx_raw)

        if '32' in rx:
            # Home switch blocked.
            # Move at constant velocity (23 KHz).
            self.s.write(b'M+23000\r')
            time.sleep(0.1)
            while True:
                # Check limit status - send every 0.8 seconds.
                self.s.write(b']\r')
                time.sleep(0.1)     
                rx = self.s.read(128).decode('utf-8')
                if '0' in rx or '2' in rx: # Not-on-a-limit-switch status is 0 when stationary, 2 when in motion.
                    break
                elif '64' in rx or '128' in rx: # If we have hit either of the extreme limit switches and stopped.
                    print('Hit edge limit switch when homing. Does this device have a home sensor?')
                    raise RuntimeError('Hit edge limit switch when homing. Does this device have a home sensor?')
                time.sleep(0.7)
            # Soft stop when homing flag is located.
            self.s.write(b'@\r')
            time.sleep(0.1) 
            # Back into home switch 3 motor revolutions.
            self.s.write(b'-108000\r')
            time.sleep(0.1) 
            # Go 2 motor revolutions up.
            self.s.write(b'+72000\r')
            time.sleep(0.1) 
            # Enable 'high accuracy' circuit.
            self.s.write(b'A24\r')
            time.sleep(0.1) 
            # Find edge of home flag at 1000 steps/sec.
            self.s.write(b'F1000,0\r')
            time.sleep(0.1) 
            time.sleep(3)
            # Disable home circuit.
            self.s.write(b'A0\r')
            time.sleep(0.1) 
            pass
        elif '0' in rx:
            # Home switch not blocked.
            # Move at constant velocity (23 KHz).
            self.s.write(b'M-23000\r')
            time.sleep(0.1)
            while True:
                # Check limit status - send every 0.8 seconds.
                self.s.write(b']\r')
                time.sleep(0.1)     
                rx = self.s.read(128).decode('utf-8')
                if '32' in rx or '34' in rx: # Home-switch-blocked status is 32 when stationary, 34 when in motion.
                    break
                elif '64' in rx or '128' in rx: # If we have hit either of the extreme limit switches and stopped.
                    # TODO: Some 789s don't have a limit switch. In this case, we will need to home using the lower limit switch... ?
                    print('Hit edge limit switch when homing. Does this device have a home sensor?')
                    raise RuntimeError('Hit edge limit switch when homing. Does this device have a home sensor?')
                time.sleep(0.7)
            # Soft stop when homing flag is located.
            self.s.write(b'@\r')
            time.sleep(0.1) 
            # Back into home switch 3 motor revolutions.
            self.s.write(b'-108000\r')
            time.sleep(0.1) 
            # Go 2 motor revolutions up.
            self.s.write(b'+72000\r')
            time.sleep(0.1) 
            # Enable 'high accuracy' circuit.
            self.s.write(b'A24\r')
            time.sleep(0.1) 
            # Find edge of home flag at 1000 steps/sec.
            self.s.write(b'F1000,0\r')
            time.sleep(0.1) 
            time.sleep(3)
            # Disable home circuit.
            self.s.write(b'A0\r')
            time.sleep(0.1) 
            pass
        else:
            print('Unknown position to home from.', rx)
            raise RuntimeError('Unknown position to home from.')

        # The standard is for the device drivers to read 0 when homed if the controller does not itself provide a value.
        # It is up to the middleware to handle zero- and home-offsets.
        self._position = 0
        self._is_homing = False
        return True

    def get_position(self):
        return self._position

    def is_moving(self):
        self.s.write(b'^\r')
        status = self.s.read(128).decode('utf-8').rstrip()
        
        if '0' in status:
            self._moving = False
            return False
        else:
            self._moving = True
            return True

    def is_homing(self):
        return self._is_homing

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, block: bool):
        steps = position - self._position
        self.move_relative(steps, block)

    def move_relative(self, steps: int, block: bool):
        print('Being told to move %d steps.'%(steps))

        if steps > 0:
            print('Moving...')
            print(b'+%d\r'%(steps))
            self.s.write(b'+%d\r'%(steps))
            time.sleep(0.1)
        elif steps < 0:
            print('Moving...')
            print(b'-%d\r'%(steps * -1))
            self.s.write(b'-%d\r'%(steps * -1))
            time.sleep(0.1)
        else:
            print('Not moving (0 steps).')
            return
        
        if block:
            i=0
            # moving = True
            while i<3:
                print('BLOCKING')
                time.sleep(0.5)
                if not self.is_moving():
                    print('Found to be NOT MOVING.',i)
                    i+=1
                else:
                    print('Found to be MOVING',i)
                    i=0
            print('FINISHED BLOCKING because moving is', i)
        time.sleep(0.25)

        self._position += steps
        
        # self.s.write(b'+%d\r'%(steps))
        # self._position += steps

    def short_name(self):
        return self.s_name

    def long_name(self):
        return self.l_name

class MP_789A_4_DUMMY:
    def __init__(self, port):
        self.s_name = 'MP789_DUMMY'
        self.l_name = 'McPherson 789A-4 (DUMMY)'

        print('Attempting to connect to McPherson Model 789A-4 Scan Controller on port %s.'%(port))

        if port is not None:     
            print('McPherson model 789A-4 (DUMMY) Scan Controller generated.')
        
        self._position = 0
        self._moving = False
        self.home()

    def home(self)->bool:
        print('Beginning home.')
        print('Finished homing.')
        success = True

        if success:
            self._position = 0

        return success

    def get_position(self):
        return self._position

    def is_moving(self):
        return self._moving

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, block: bool):
        steps = position - self._position
        # Stops the moving updater from starting more than once.
        self.move_relative(steps, block)

    def move_relative(self, steps: int, block: bool):
        print(b'+%d\r', steps)
        self._position += steps

        if block:
            i=0
            # moving = True
            while i<15:
                print('BLOCKING')
                time.sleep(0.5)
                if not self.is_moving():
                    print('Found to be NOT MOVING.',i)
                    i+=1
                else:
                    print('Found to be MOVING',i)
                    i=0
            print('FINISHED BLOCKING because moving is', i)
        time.sleep(0.25)


    def short_name(self):
        return self.s_name

    def long_name(self):
        return self.l_name

""" 
McPherson Model 789A-4 Scan Controller Command Set

ASCII       Value   Desc.
-----------------------------------------------
[SPACE]     0x20    Init   
[CR]        0x0D    Carriage Return
@                   Soft Stop
A0                  Set Home Switch OFF
A8                  Set Home Switch ON
A24                 Enable Homing Circuit
^C          0x03    Reset
C1                  Clear
F1000,0             Find Home
G                   Run Internal Program
I                   Starting Velocity
K                   Ramp Slope
P                   Enter & Exit Program Mode
S                   Save
V                   Scanning Velocity
X                   Examine Parameters
]                   Read Limit Switch Status
+                   Index Scan In Up Direction
-                   Index Scan In Down Direction
^                   Read Moving Status
"""
