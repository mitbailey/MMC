#
# @file mp_792.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Driver for the McPherson Series 792 multi-axis Motor Controller.
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
from utilities import safe_serial

from drivers.mp_789a_4 import MP_789A_4
from drivers.mp_789a_4 import MP_789A_4_DUMMY

class MP_792:
    AXES = [b'A0', b'A8', b'A16', b'A24']

    def __init__(self, port: serial.Serial, axes: int = 4):
        self.num_axes = axes
        self.s_name = 'MP792'
        self.l_name = 'McPherson 792'
        self.axis_alive = [False] * axes
        self._is_homing = [False] * axes
        self._is_moving_l = [False] * axes
        self.current_axis = 0

        if port is None:
            print('Port is none type.')
            raise RuntimeError('Port is none type.')

        print('Attempting to connect to McPherson 792 on port %s.'%(port))

        self._position = [0] * 4

        ser_ports = ports_finder.find_serial_ports()
        if port not in ser_ports:
            print('Port not valid. Is another program using the port?')
            print('%s\nnot found in\n%s'%(port, ser_ports))
            raise RuntimeError('Port not valid. Is another program using the port?')

        self.s = safe_serial.SafeSerial(port, 9600, timeout=1)
        self.s.write(b' \r')
        time.sleep(0.1)
        rx = self.s.read(128)#.decode('utf-8').rstrip()
        print(rx)

        if rx is None or rx == b'':
            raise RuntimeError('Response timed out.')
        elif rx == b' v2.55\r\n#\r\n':
            print('McPherson model 792 Scan Controller found.')
        elif rx == b' #\r\n':
            print('McPherson model 792 Multi-Axis already initialized.')
        else:
            raise RuntimeError('Invalid response.')

        print('Checking axes...')
        for i in range(4):
            print('WR:', MP_792.AXES[i] + b'\r')
            self.s.write(MP_792.AXES[i] + b'\r')
            time.sleep(0.1)
            print('RD:', self.s.read(128))
            time.sleep(0.1)

            print('WR:', b']\r')
            self.s.write(b']\r')
            time.sleep(0.1)
            alivestat = self.s.read(128).decode('utf-8')
            print('RD:', alivestat)
            time.sleep(0.1)

            if '192' in alivestat:
                print('Axis %d is dead.'%(i))
                self.axis_alive[i] = False
            else:
                print('Axis %d is alive.'%(i))
                self.axis_alive[i] = True

                self.home(i)

        print('McPherson 792 initialization complete.')

    def set_axis(self, axis: int):
        if axis != self.current_axis:
            print('WR:', MP_792.AXES[axis] + b'\r')
            self.s.write(MP_792.AXES[axis] + b'\r')
            time.sleep(0.1)
            print('RD:', self.s.read(128))
            self.current_axis = axis
            time.sleep(0.5)

    def home(self, axis: int)->bool:
        self.set_axis(axis)

        print('Beginning home for 792 axis %d.'%(axis))
        self._is_homing[axis] = True

        print('WR:', b'M-10000\r')
        self.s.write(b'M-10000\r')
        time.sleep(0.1)
        print('RD:', self.s.read(128))

        start_time = time.time()
        retries = 3
        success = True
        while True:
            current_time = time.time()

            moving = self._is_moving(axis)
            time.sleep(0.1)

            self.s.write(b']\r')
            time.sleep(0.1)
            limstat = self.s.read(128).decode('utf-8')
            print('limstat:', limstat)

            if moving:
                print('Moving...')
            if '0' not in limstat:
                print('Not yet homed...')
            
            if not moving and '128' in limstat:
                print('Moving has completed - homing successful.')
                break
            elif (not moving and '128' not in limstat) or (current_time - start_time > 60):
                print('Moving has completed - homing failed.')
                if retries == 0:
                    print('Homing failed.')
                    self._is_homing[axis] = False
                    return False
                else:
                    print('Retrying homing...')
                    retries -= 1

                    print('WR:', b'M-10000\r')
                    self.s.write(b'M-10000\r')
                    time.sleep(0.1)
                    print('RD:', self.s.read(128))

                    start_time = time.time()

            time.sleep(0.5)

        if (self.is_moving(axis)):
            print('Post-home movement detected. Entering movement remediation.')
            self.s.write(b'@\r')
            time.sleep(1)
        stop_waits = 0
        while(self.is_moving(axis)):
            if stop_waits > 3:
                stop_waits = 0
                print('Re-commanding that device ceases movement.')
                self.s.write(b'@\r')
            stop_waits += 1
            print('Waiting for device to cease movement.')
            time.sleep(1)

        self._position[axis] = 0
        self._is_homing[axis] = False
        return True

    def get_position(self, axis: int):
        return self._position[axis]

    def is_moving(self, axis: int):
        return self._is_moving_l[axis]

    def _is_moving(self, axis: int):
        self.set_axis(axis)

        self.s.write(b'^\r')
        time.sleep(0.1)
        status = self.s.read(128).decode('utf-8').rstrip()
        print('792 _status:', status)
        time.sleep(0.1)
        self.s.write(b'^\r')
        time.sleep(0.1)
        status2 = self.s.read(128).decode('utf-8').rstrip()
        print('792 _status2:', status2)

        if ('0' in status and '0' in status2) and ('+' not in status and '+' not in status2 and '-' not in status and '-' not in status2):
            self._is_moving_l[axis] = False
            return False
        else:
            self._is_moving_l[axis] = True
            return True

    def is_homing(self, axis: int):
        return self._is_homing[axis]

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, block: bool, axis: int):
        self.set_axis(axis)

        steps = position - self._position[axis]
        self.move_relative(steps, block, axis)

    def move_relative(self, steps: int, block: bool, axis: int):
        self.set_axis(axis)

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
        self._position[axis] += steps

        if block:
            i=0
            # moving = True
            while i<3:
                print('BLOCKING')
                time.sleep(0.2)
                if not self._is_moving(axis):
                    print('Found to be NOT MOVING.')
                    i+=1
            print('FINISHED BLOCKING because moving is', i)
        time.sleep(0.25)

    def short_name(self):
        return self.s_name

    def long_name(self):
        return self.l_name

class MP_792_DUMMY:
    AXES = [b'A0', b'A8', b'A16', b'A24']

    def __init__(self, port: serial.Serial, axes: int = 4):
        self.num_axes = axes
        self.s_name = 'MP792'
        self.l_name = 'McPherson 792'
        self.axis_alive = [False] * axes
        self._is_homing = [False] * axes
        self._is_moving_l = [False] * axes
        self.current_axis = 0

        if port is None:
            print('Port is none type.')
            raise RuntimeError('Port is none type.')

        print('Attempting to connect to McPherson 792 on port %s.'%(port))

        self._position = [0] * 4

        print('Checking axes...')
        for i in range(4):
            print('WR:', MP_792.AXES[i] + b'\r')
            time.sleep(0.1)

            print('WR:', b']\r')
            
            time.sleep(1.5)
            
            print('RD:', 'Dummy - Axes Always Alive')
            time.sleep(0.1)


            print('Axis %d is alive.'%(i))
            self.axis_alive[i] = True

            self.home(i)

        time.sleep(5)

        print('McPherson 792 initialization complete.')

    def set_axis(self, axis: int):
        if axis != self.current_axis:
            print('WR:', MP_792.AXES[axis] + b'\r')
            self.current_axis = axis
            time.sleep(0.1)

    def home(self, axis: int)->bool:
        self.set_axis(axis)

        print('Beginning home for 792 axis %d.'%(axis))
        self._is_homing[axis] = True

        print('WR:', b'M-10000\r')
        time.sleep(0.5)

        start_time = time.time()
        retries = 3
        success = True
        
        # The standard is for the device drivers to read 0 when homed if the controller does not itself provide a value.
        # It is up to the middleware to handle zero- and home-offsets.
        self._position[axis] = 0
        self._is_homing[axis] = False
        return True

    def get_position(self, axis: int):
        return self._position[axis]

    def _is_moving(self, axis: int):
        self.set_axis(axis)

        self._is_moving_l[axis] = False
        return False

    def is_moving(self, axis: int):
        return self._is_moving_l[axis]

    def is_homing(self, axis: int):
        return self._is_homing[axis]

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, block: bool, axis: int):
        self.set_axis(axis)

        steps = position - self._position[axis]
        self.move_relative(steps, block, axis)

    def move_relative(self, steps: int, block: bool, axis: int):
        self.set_axis(axis)

        self._position[axis] += steps

        if block:
            while self._is_moving(axis):
                print('BLOCKING')
                time.sleep(0.5)
            print('FINISHED BLOCKING')


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
