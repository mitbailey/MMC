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
from .stagedevice import StageDevice
import time
from typing import Iterable, List
from time import sleep
from utilities import log
from threading import Lock

from .thorlabs_net import *


def __funcname__():
    import inspect
    return inspect.stack()[1][3]


# TODO add back relative import


def wrap_result(err_type=RuntimeError, err_msg=''):
    def decorate(f):
        def applicator(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                err = err_type(f'{f.__name__}({args}, {kwargs}): {err_msg} {e}')
                log.error(err)
                raise err

        return applicator

    return decorate


@wrap_result()
def build_device_list():
    return DeviceManagerCLI.BuildDeviceList()


@wrap_result()
def get_device_list() -> List[str]:
    return list(DeviceManagerCLI.GetDeviceList())


class ThorlabsKST101(StageDevice):
    OPEN_DEVICES = {}
    LOCK = Lock() # Lock for OPEN_DEVICES

    def backend(self)->str:
        return 'Thorlabs'

    def list_devices():
        build_device_list()
        return get_device_list()

    @staticmethod
    @wrap_result()
    def _get_device_info(device) -> dict:
        info = device.GetDeviceInfo()
        return {
            'typeId': info.DeviceType,
            'model_no': info.Name,
            'description': info.Description,
            'serial_no': info.SerialNumberText,
            'fw_ver': str(info.FirmwareVersion),
        }

    @staticmethod
    def get_device_info(serialNumber: int | str | Iterable) -> dict:
        """Get Device Info for a given Thorlabs Serial Number.

            Args:
                typeID (int | list(int)): Thorlabs Serial Numbers.

            Raises:
                RuntimeError: Could not get device info for serial.

            Returns:
                dict: Device Information (struct TLI_DeviceInfo)
        """

        if isinstance(serialNumber, int):
            ser = [str(serialNumber),]
        elif isinstance(serialNumber, str):
            ser = [serialNumber,]
        elif isinstance(serialNumber, Iterable):
            ser = list(map(str, serialNumber))
        else:
            raise TypeError('Serial number can be an int or a list of int.')

        out = []
        with ThorlabsKST101.LOCK:
            for s in ser:
                if s in ThorlabsKST101.OPEN_DEVICES:
                    return ThorlabsKST101.OPEN_DEVICES[s]
                try:
                    device = KCubeStepper.CreateKCubeStepper(s)
                    device.Connect(s)
                    out.append(ThorlabsKST101._get_device_info(device))
                    device.Disconnect()
                except Exception as e:
                    raise RuntimeError(
                        f'Could not get device info for serial {s}. {e}')

            if len(out) == 1:
                return out[0]
            return out

    def __init__(self, ser=int, pollingIntervalMs: int = 250):
        """Create an instance of Thorlabs KST101 Stepper Motor Controller

            Args:
                serialNumber (int): Serial number of the KST101 Controller

            Raises:
                ValueError: Invalid serial number
                RuntimeError: Instance of KST101 exists with this serial number
                RuntimeError: Serial number not in device list
        """
        self._home_speed_mult = 1
        self._move_speed_mult = 1
        self._dev = None
        with ThorlabsKST101.LOCK:
            try:
                self._dev = KCubeStepper.CreateKCubeStepper(ser)
                self.serial = str(ser)
                self._initialize(pollingIntervalMs)
                self._stage = None
                info = self._get_device_info(self._dev)
                ThorlabsKST101.OPEN_DEVICES[self.serial] = info
                self._pos = None
            except Exception as e:
                log.error(f'Failed to open device: {e}')
                sleep(1)
        # self._dev.open() # <-- Auto-called.
        # https://pylablib.readthedocs.io/en/latest/devices/Thorlabs_kinesis.html#stages-thorlabs-kinesis
        # https://pylablib.readthedocs.io/en/stable/devices/devices_basics.html
        # Section "Connection"

    def _initialize(self, pollingIntervalMs: int = 250) -> bool:
        """Open connection to the KST101 Controller.

        Raises:
            RuntimeError: Connection to device is already open.
            RuntimeError: Error opening connection to device.

        Returns:
            bool: _description_
        """
        try:
            ret = KCubeStepper.CreateKCubeStepper(self.serial)
            ret.Connect(self.serial)
            self._dev = ret
            time.sleep(0.25)
            use_file_settings = DeviceConfiguration.DeviceSettingsUseOptionType.UseFileSettings
            device_config = ret.LoadMotorConfiguration(
                ret.DeviceID, use_file_settings)
            # Get homing settings
            home_params = ret.GetHomingParams()
        except Exception as e:
            raise RuntimeError(
                'Could not open connection to device %s: %s' % (self.serial, e))

        # Run self connection test.
        # ret = self._CheckConnection(self.serial)
        ret = self._CheckConnection()
        if ret == False:
            self._Close()
            raise RuntimeError('Device opened but connection test failed.')
        self._StartPolling(pollingIntervalMs)
        return True

    @wrap_result()
    def _Close(self) -> None:
        """Close connection to the KST101 Controller.
        """
        with ThorlabsKST101.LOCK:
            if self._dev is not None:
                self._StopPolling()
                self._dev.Disconnect()
                del ThorlabsKST101.OPEN_DEVICES[self.serial]

    @wrap_result()
    def _StopPolling(self):
        self._dev.StopPolling()

    @wrap_result()
    def _StartPolling(self, rate_ms: int):
        self._dev.StartPolling(rate_ms)
        return True

    @wrap_result()
    def _CheckConnection(self) -> bool:
        """Check connection to the device.

        Returns:
            bool: True if the device is connected.
        """
        return DeviceManagerCLI.IsDeviceConnected(self.serial)

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

    @wrap_result()
    def home(self, timeout_ms: int = 90000):
        log.info('Beginning home...')
        self._dev.Home(timeout_ms)

    @wrap_result()
    def get_position(self):
        state = self._dev.State
        pos = self._dev.Position_DeviceUnit
        if state == MotorStates.Idle: # idle
            self._pos = pos
        # log.trace(f'Position: {self._pos} | {pos}')
        ret = 0 if self._pos is None else self._pos
        return ret

    @wrap_result()
    def stop(self):
        # TODO: Figure out if there is another method, besides Homing, that will re-enable movement.
        # TODO: Scan stop should be different from an All Stop - right now theyre all the same, this needs to change such that scan stops wont require a homing.
        self._dev.Stop(0)
        time.sleep(5)
        self.home() # KST201 requires a homing after a stop, otherwise it doesnt move at all.

    @wrap_result()
    def _get_state(self):
        return self._dev.State

    def is_moving(self):
        state = self._get_state()
        return (state == MotorStates.Moving) or (state == MotorStates.Homing)

    def is_homing(self):
        state = self._get_state()
        return state == MotorStates.Homing

    @wrap_result()
    def move_to(self, position: int, backlash: int = None, timeout_ms: int = 60000):
        # "Cannot move to requested position" likely means it wasn't homed and is trying to move beyond its limit.

        # retries = 0
        # while True:
            # log.info(f'{retries}: Requesting a move to {position}, (int) {int(position)}, (Int32) {Int32(position)} with timeout_ms {timeout_ms}.')
        log.info(f'Requesting a move to {position} with timeout_ms {timeout_ms}.')
        # position = int(position)
        # position = Int32(position)

        try:
            self._dev.MoveTo_DeviceUnit(position, timeout_ms)
            # self._dev.MoveTo(Decimal(26.0), timeout_ms)
        except Exception as e:
            log.error(f'KST failed to move to position {position} because: {e}')
            if 'Cannot move to requested position' in str(e):
                log.error(f"The position index {position} may be beyond the motor's maximum limit and it is therefore unable to move further.")
            # time.sleep(1)
            # retries += 1
            # log.info(f'Attempting retry {retries} for this move command.')
            #     continue
            # break

    @wrap_result()
    def move_relative(self, steps: int, timeout_ms: int = 60000):
        steps = int(steps)
        if steps == 0:
            return
        movdir = MotorDirection.Forward if steps > 0 else MotorDirection.Backward
        self._dev.MoveRelative_DeviceUnit(movdir, Int32(abs(steps)), timeout_ms)

    def set_home_speed_mult(self, speed):
        self._home_speed_mult = speed

    def set_move_speed_mult(self, speed):
        self._move_speed_mult = speed

    def short_name(self):
        return 'KSTX01'

    def long_name(self):
        return 'Thorlabs ' + self.short_name()

# %%


class KSTDummy(StageDevice):
    WR_DLY = 0.1

    def list_devices():
        devlist = []
        devlist.append('DUMMY_DEVICE_1')
        return devlist

    def backend(self) -> str:
        return 'Thorlabs'
    
    def __init__(self, port):
        log.info(
            'Attempting to connect to McPherson Model 789A-4 Scan Controller on port %s.' % (port))

        if port is not None:
            log.info('McPherson model 789A-4 (DUMMY) Scan Controller generated.')
        self._home_speed_mult = 1
        self._move_speed_mult = 1
        self._position = 0
        self._moving = False
        self._homing = False
        self.home()
        time.sleep(KSTDummy.WR_DLY)

    def home(self) -> bool:
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
    
    def is_homing(self):
        log.debug('func: is_homing')
        return self._homing

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

        i = 0
        # moving = True
        while i < 15:
            log.debug('BLOCKING')
            time.sleep(KSTDummy.WR_DLY)
            if not self.is_moving():
                log.info('Found to be NOT MOVING.', i)
                i += 1
            else:
                log.info('Found to be MOVING', i)
                i = 0
        log.debug('FINISHED BLOCKING because moving is', i)
        time.sleep(KSTDummy.WR_DLY)

    def set_home_speed_mult(self, speed):
        self._home_speed_mult = speed

    def set_move_speed_mult(self, speed):
        self._move_speed_mult = speed

    def short_name(self):
        return 'KSTX01 DUMMY'

    def long_name(self):
        return 'Thorlabs ' + self.short_name()


# %%

if __name__ == '__main__':
    from pprint import pprint

    serials = ThorlabsKST101.list_devices()
    print('Serial number(s): ', end='')

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
        STEPS_PER_VALUE = 2184560.64  # 7471104

        # DESIRED_POSITION_NM = 0

        DESIRED_POSITION_MM = 5

        DESIRED_POSITION_IDX = int(DESIRED_POSITION_MM * STEPS_PER_VALUE)
        retval = motor_ctrl.move_to(DESIRED_POSITION_IDX)

        print('Final position: ' + str(motor_ctrl.get_position()))
        retval = motor_ctrl.move_relative(
            DESIRED_POSITION_IDX * 2)  # another 10 mm

# %%
