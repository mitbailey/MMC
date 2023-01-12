#
# @file mp_789a_4.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Driver for the McPherson Model 789A-4 Scan Controller.
# @version See Git tags for version information.
# @date 2022.11.04
# 
# @copyright Copyright (c) 2022
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

        print('Attempting to connect to McPherson Model 789A-4 Scan Controller on port %s.'%(port))

        # TODO: Change default.
        self.steps_per_value = 1

        if port is not None:     
            self._position = 0
            # self.port = -1

            ser_ports = ports_finder.find_serial_ports()
            if port not in ser_ports:
                print('Port not valid. Is another program using the port?')
                raise RuntimeError('Port not valid. Is another program using the port?')

            self.s = serial.Serial(port, 9600, timeout=1)
            self.s.write(b' \r')
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

            self.s.write(b'C1\r')
            time.sleep(0.1)

        if self.s is None:
            raise RuntimeError('self.s is None')

        self.home()

    def home(self)->bool:
        print('Beginning home.')
        self._is_homing = True
        print('WR:', b'A24\r')
        self.s.write(b'A24\r') # Enable Homing Circuit
        time.sleep(0.5)
        print('RD:', self.s.read(128))
        print('WR:', b'A8\r')
        self.s.write(b'A8\r') # Set Home Switch "ON"
        time.sleep(0.5)
        print('RD:', self.s.read(128))
        print('WR:', b'F1000,0\r')
        self.s.write(b'F1000,0\r') # Searches for home.
        time.sleep(0.5)
        print('RD:', self.s.read(128))

        start_time = time.time()
        retries = 0
        success = True
        while True:
            current_time = time.time()
            if current_time - start_time > 60:
                if retries > 3:
                    print('Giving up trying to home after three tries.')
                    success = False
                    break
                retries += 1
                print('Not homed after 60 seconds. Repeating command.')
                start_time = current_time
                print('WR:', b'F1000,0\r')
                self.s.write(b'F1000,0\r')
                time.sleep(0.5)
                print('RD:', self.s.read(128))
            print('WR:', b']\r')
            self.s.write(b']\r')
            time.sleep(0.5)
            rx = self.s.read(128).decode('utf-8').rstrip()
            print('Rx:', rx)
            if '32' in rx:
                print('Finished homing.')
                success = True
                break
            else:
                print('Still homing...')
            time.sleep(0.5)
        
        self.s.write(b'A0\r') # Set home switch off.
        time.sleep(0.5)
        print(self.s.read(128))

        if success:
            self._position = 0

            self.write(b'\x03\r') # Resets counter.
            time.sleep(0.5)
            print(self.s.read(128))

        self._is_homing = False
        return success

    def get_position(self):
        return self._position

    def is_moving(self):
        self.s.write(b'^\r')
        status = self.s.read(128).decode('utf-8').rstrip()
        print('789a-4 status:', status)
        if '0' in status:
            return False
        else:
            return True

    def is_homing(self):
        return self._is_homing

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, block: bool):
        steps = position - self._position
        self.move_relative(steps, block)

    def move_relative(self, steps: int, block: bool):
        self.s.write(b'+%d\r', steps)
        self._position += steps

    def short_name(self):
        return self.s_name

    def long_name(self):
        return self.l_name

class MP_789A_4_DUMMY:
    def __init__(self, port):
        self.s_name = 'MP789_DUMMY'
        self.l_name = 'McPherson 789A-4 (DUMMY)'

        print('Attempting to connect to McPherson Model 789A-4 Scan Controller on port %s.'%(port))

        # TODO: Change default.
        self.steps_per_value = 1

        if port is not None:     
            print('McPherson model 789A-4 (DUMMY) Scan Controller generated.')
        
        self._position = 0
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
        return False

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, block: bool):
        steps = position - self._position
        self.move_relative(steps, block)

    def move_relative(self, steps: int, block: bool):
        print(b'+%d\r', steps)
        self._position += steps

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
