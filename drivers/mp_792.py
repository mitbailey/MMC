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
from mp_789a_4 import MP_789A_4

class MP_792:
    AXES = [b'A0', b'A8', b'A16', b'A24']

    def __init__(self, port: serial.Serial):
        if port is None:
            raise RuntimeError('Port is none type.')

        print('Attempting to connect to McPherson 792 on port %s.'%(port))

        self._position = [0] * 4

        ser_ports = ports_finder.find_serial_ports()
        if port not in ser_ports:
            print('Port not valid.')
            raise RuntimeError('Port not valid.')

        self.s = serial.Serial(port, 9600, timeout=1)
        self.s.write(b' \r')
        rx = self.s.read(128).decode('utf-8').rstrip()
        print(rx)

        if rx is None or rx == b'':
            raise RuntimeError('Response timed out.')
        elif '#' in rx:
            print('McPherson model 789A-4 Scan Controller found.')
        else:
            raise RuntimeError('Invalid response.')

        self.s.write(b'C1\r')
        time.sleep(0.1)

        self._V_789 = MP_789A_4(None)

        print('McPherson 792 initialization complete.')

        self.current_axis = 0

    def _confirm_axis(self, axis: int):
        if axis != self.current_axis:
            self.s.write(MP_792[self.current_axis] + '\r')
            time.sleep(0.1)

    def home(self, axis: int):
        self.confirm_axis()
        return self._V_789.home()

    def position(self, axis: int):
        self.confirm_axis()
        return self._V_789.position()

    def is_moving(self, axis: int):
        self.confirm_axis()
        return self._V_789.is_moving()

    def move_to(self, axis: int, position: int):
        self.confirm_axis()
        self._V_789.move_to(position)

    def move_relative(self, axis: int, steps: int):
        self.confirm_axis()
        self._V_789.move_relative(steps)

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
