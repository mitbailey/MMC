#
# @file mp_792.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Driver for the McPherson Series 792 multi-axis Motor Controller.
# @version See Git tags for version information.
# @date 2022.11.04
# 
# @copyright Copyright (c) 2022
# 
#

import serial
import time
from utilities import ports_finder

from drivers.mp_789a_4 import MP_789A_4
from drivers.mp_789a_4 import MP_789A_4_DUMMY

class MP_792:
    AXES = [b'A0', b'A8', b'A16', b'A24']

    def __init__(self, port: serial.Serial, axes: int = 4):
        self.num_axes = axes
        self.s_name = 'MP782'
        self.l_name = 'McPherson 782'

        if port is None:
            print('Port is none type.')
            raise RuntimeError('Port is none type.')

        # TODO: Change default.
        self.mm_to_idx = 1

        print('Attempting to connect to McPherson 792 on port %s.'%(port))

        self._position = [0] * 4

        ser_ports = ports_finder.find_serial_ports()
        if port not in ser_ports:
            print('Port not valid.')
            raise RuntimeError('Port not valid.')

        self.s = serial.Serial(port, 9600, timeout=1)
        self.s.write(b' \r')
        rx = self.s.read(128)#.decode('utf-8').rstrip()
        print(rx)

        if rx is None or rx == b'':
            raise RuntimeError('Response timed out.')
        elif rx == b' v2.55\r\n#\r\n' or rx == b' #\r\n':
            print('McPherson model 789A-4 Scan Controller found.')
        else:
            raise RuntimeError('Invalid response.')

        self.s.write(b'C1\r')
        time.sleep(0.1)

        print('McPherson 792 initialization complete.')

        self.current_axis = 0

    def set_axis(self, axis: int):
        if axis != self.current_axis:
            self.s.write(MP_792.AXES[axis] + '\r')
            self.current_axis = axis
            time.sleep(0.1)

    def short_name(self):
        return self.s_name

    def long_name(self):
        return self.l_name

class MP_792_DUMMY:
    AXES = [b'A0', b'A8', b'A16', b'A24']

    def __init__(self, port: serial.Serial, axes: int = 4):
        self.num_axes = axes
        self.s_name = 'MP782'
        self.l_name = 'McPherson 782'
        self.s = None

        if port is None:
            print('Port is none type.')
            raise RuntimeError('Port is none type.')

        # TODO: Change default.
        self.mm_to_idx = 1

        print('Attempting to connect to McPherson 792 on port %s.'%(port))

        self._position = [0] * 4

        print('McPherson model 789A-4 (DUMMY) Scan Controller generated.')

        print('McPherson 792 initialization complete.')

        self.current_axis = 0

    def set_axis(self, axis: int):
        if axis != self.current_axis:
            print('self.write(): ', MP_792_DUMMY.AXES[axis], '\r')
            self.current_axis = axis
            print('Current axis:', self.current_axis)
            time.sleep(0.1)

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
