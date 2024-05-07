#
# @file _thorlabs_kst_advanced.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief High-level ThorLabs KST driver wrapper.
# @version See Git tags for version information.
# @date 2024.05.06
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

# %% Imports
from __future__ import annotations
import sys
import time
from typing import List
import weakref
import warnings
from time import sleep
import threading
from utilities import log
from pylablib.devices.Thorlabs import KinesisMotor, KinesisDevice, list_kinesis_devices

def __funcname__():
    import inspect
    return inspect.stack()[1][3]

# TODO add back relative import
from .stagedevice import StageDevice

class ThorlabsKST101(StageDevice):
    def list_devices():
        ret = list_kinesis_devices(filter_ids=True)
        ret = [x for x, _ in ret]
        ret = filter(lambda x: x[:2] == '26', ret)
        return list(map(int, ret))
    
    @staticmethod
    def get_device_info(ser: int):
        dev = KinesisDevice(ser)
        dev.open()
        ret = dev.get_device_info()._asdict()
        dev.close()
        del dev
        return ret

    def __init__(self, ser=int):
        self._dev = KinesisMotor(ser)
        self._dev.open()
        self._stage = None
        # self._dev.open() # <-- Auto-called.
        # https://pylablib.readthedocs.io/en/latest/devices/Thorlabs_kinesis.html#stages-thorlabs-kinesis
        # https://pylablib.readthedocs.io/en/stable/devices/devices_basics.html
        # Section "Connection"

    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()

    def open(self):
        return
    
    def close(self):
        self._dev.close()

    def set_stage(self, stage: str):
        self._stage = stage

    def get_stage(self):
        return self._stage

    def home(self):
        self._dev.home(force=True, sync=True) # <-- use the non-blocking version, since QThread is panicking.
        while self._dev.is_moving():
            sleep(0.1)

    def get_position(self):
        return self._dev.get_position()
    
    def stop(self):
        self._dev.stop()

    def is_moving(self):
        return self._dev.is_moving()

    def is_homing(self):
        return self._dev.is_homing()

    def move_to(self, position: int, backlash: int=None):
        self._dev.move_to(position)

    def move_relative(self, steps: int):
        self._dev.move_by(steps) 

    def short_name(self):
        return 'KSTX01'

    def long_name(self):
        return 'Thorlabs ' + self.short_name()
        
# %%
class KSTDummy(StageDevice):
    def __init__(self, port):
        self.s_name = 'MP789_DUMMY'
        self.l_name = 'McPherson 789A-4 (DUMMY)'

        log.info('Attempting to connect to McPherson Model 789A-4 Scan Controller on port %s.'%(port))

        if port is not None:     
            log.info('McPherson model 789A-4 (DUMMY) Scan Controller generated.')
        
        self._position = 0
        self._moving = False
        self.home()
        time.sleep(KSTDummy.WR_DLY * 50)

    def home(self)->bool:
        log.debug('func: home')
        log.info('Beginning home.')
        log.info('Finished homing.')
        success = True

        if success:
            self._position = 0

        return success

    def get_position(self):
        log.debug('func: get_position')
        return self._position
    
    # Triple-redundant serial stop command.
    def stop(self):
        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(KSTDummy.WR_DLY)

        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(KSTDummy.WR_DLY)

        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(KSTDummy.WR_DLY)

    def is_moving(self):
        log.debug('func: is_moving')
        return self._moving

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, backlash: int):
        log.debug('func: move_to')
        steps = position - self._position

        # Stops the moving updater from starting more than once. <-- Huh?

        if (steps < 0) and (backlash > 0):
            self.move_relative(steps - backlash)
            self.move_relative(backlash)
        else:
            self.move_relative(steps)

    def move_relative(self, steps: int):
        log.debug('func: move_relative')
        log.debug(b'+%d\r', steps)
        self._position += steps

        i=0
        # moving = True
        while i<15:
            log.debug('BLOCKING')
            time.sleep(KSTDummy.WR_DLY * 5)
            if not self.is_moving():
                log.info('Found to be NOT MOVING.',i)
                i+=1
            else:
                log.info('Found to be MOVING',i)
                i=0
        log.debug('FINISHED BLOCKING because moving is', i)
        time.sleep(KSTDummy.WR_DLY * 2.5)


    def short_name(self):
        log.debug('func: short_name')
        return self.s_name

    def long_name(self):
        log.debug('func: long_name')
        return self.l_name


# %%  

if __name__ == '__main__':
    from pprint import pprint

    serials = ThorlabsKST101.list_devices()
    print('Serial number(s): ', end = '')

    print("INITIALIZING DEVICE")
    with ThorlabsKST101(serials[0]) as motor_ctrl:
        sleep(1)
        

        print('Current position: ' + str(motor_ctrl.get_position()))
        sleep(1)

        motor_ctrl.home()
        print(motor_ctrl.set_stage('ZST25'))
        print("ATTEMPTING TO MOVE")

        # MM_TO_NM = 10e6
        # STEPS_PER_VALUE = 2184532 # Based on motor/stage...
        STEPS_PER_VALUE = 2184560.64 # 7471104

        # DESIRED_POSITION_NM = 0

        DESIRED_POSITION_MM = 5

        DESIRED_POSITION_IDX = int(DESIRED_POSITION_MM * STEPS_PER_VALUE)
        retval = motor_ctrl.move_to(DESIRED_POSITION_IDX)

        print('Final position: ' + str(motor_ctrl.get_position()))
        retval = motor_ctrl.move_relative(DESIRED_POSITION_IDX * 2) # another 10 mm

# %%
