#
# @file middleware.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Provides a layer of abstraction between the MMC GUI and the underlying hardware device drivers.
# @version See Git tags for version information.
# @date 2022.09.23
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

# OS and SYS Imports
import os
import sys

try:
    exeDir = sys._MEIPASS
except Exception:
    exeDir = os.getcwd()

if getattr(sys, 'frozen', False):
    appDir = os.path.dirname(sys.executable)
elif __file__:
    appDir = os.path.dirname(__file__)

# More Standard Imports
import configparser as confp
from email.charset import QP
from time import sleep
from io import TextIOWrapper
import math as m
import numpy as np
import datetime as dt
import serial
import threading

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# Custom Imports
from drivers import _thorlabs_kst_advanced as tlkt
from drivers import ki_picoammeter as ki_pico
from drivers import mp_789a_4 as mp789
from drivers import mp_792 as mp792

from utilities import ports_finder

# Motion Controller Types
# 0 - KST101

# Detector Types
# 0 - Picoammeter, Keithley

# TODO: Need to implement external triggers when certain actions occur. Should also consider adding a trigger-only faux 'device.'

class DevFinder:
    def __init__(self):
        self.done = False
        self._master_dev_list = []

        self.device_tid = threading.Thread(target=self.device_t)
        self.device_tid.start()

    def __del__(self):
        self.done = True
        self.device_tid.join()

    def device_t(self):
        while not self.done:
            port_list = ports_finder.find_serial_ports()
            dev_name_list = port_list

            for i, port in enumerate(port_list):
                dev_name_list[i] = port_list[i] + ' ' + self.discern_comport(port_list[i])

            apt_list = ports_finder.find_apt_ports()

            self._master_dev_list = dev_name_list + apt_list

            sleep(2)

    def get_dev_list(self):
        return self._master_dev_list

    def discern_comport(self, comport: str):
        s = serial.Serial(comport, 9600, timeout=1)
        sleep(0.5)

        # For each serial port, since they're likely KEYSPAN devices, we will need to figure out what device is on the other end. 

        # Check if a 789A-4 or 792 is on this comport.
        s.write(b' \r')
        sleep(0.5)

        raw = s.read(128)

        if raw == b' v2.55\r\n#\r\n' or raw == b' #\r\n':
            # print('MP 789A-4  or MP 792 detected!')
            s.close()
            return '(MP 789A-4 or MP 792)'
        else:
            # Check if a Keithley 6485 is on this comport.
            s.write(b'*RST\r')
            sleep(0.5)
            s.write(b'*IDN?\r')
            sleep(0.5)
            raw = s.read(128)
            if b'KEITHLEY INSTRUMENTS INC.,MODEL 6485' in raw:
                s.close()
                return '(KI 6485)'
        
        s.close()
        return '(Unknown)'

def find_all_ports():
    return ports_finder.find_all_ports()

# MotionController
# Genericizes the type of motor controller.
def new_motion_controller(dummy: bool, dev_model: str, man_port: str = None):
    devs = []
    if dev_model == MotionController.SupportedDevices[2]:
        # Multi-axis device.
        if dummy:
            parent = mp792.MP_792_DUMMY(man_port)
        else:
            parent = mp792.MP_792(man_port)
        # Creates a motion controller for each axis while also not enabling dead axes.
        for i, status in enumerate(parent.axis_alive):
            if status:
                print('Creating motion controller for axis ', i)
                devs.append(MotionController(dummy, 'MP_792_AXIS_%d'%(i), man_port, i, parent))
    else:
        # Single-axis device.
        devs.append(MotionController(dummy, dev_model, man_port))
    return devs

class MotionController:
    """Provides a layer of abstraction for communication with motion controller drivers.
    """
    SupportedDevices = ['TL KST101', 'MP 789A-4', 'MP 792']

    def __init__(self, dummy: bool, dev_model: str, man_port: str = None, axis: int = 0, parent = None):
        """_summary_

        Args:
            dummy (bool): Is this a fake device? If no, it must be connected hardware.
            dev_model (str): Name of the device; i.e., 'MP 789A-4'.
            man_port (str, optional): A manually defined port. Defaults to None.
            axis (int, optional): Which axis this is for, if this is for a multi-axis device. Defaults to 0.
            parent (_type_, optional): _description_. Defaults to None.

        Raises:
            RuntimeError: _description_
            RuntimeError: _description_
            Exception: _description_
            RuntimeError: _description_
        """
        self._model = dev_model
        self._steps_per_value = 0.0
        self._is_dummy = dummy
        self._motor_ctrl = None
        self._port = None
        self._axis = 0
        self._multi_axis = False

        self._max_pos = 9999
        self._min_pos = -9999

        self._homing = False
        self._moving = False

        # Initializes our motor_ctrl stuff depending on what hardware we're using.
        if self._model == MotionController.SupportedDevices[0]:
            if dummy:
                serials = tlkt.Thorlabs.KSTDummy._ListDevices()
                self._motor_ctrl = tlkt.Thorlabs.KSTDummy(serials[0])
                self._motor_ctrl.set_stage('ZST25')
            else:
                print("Trying...")
                serials = tlkt.Thorlabs.ListDevicesAny()
                print(serials)
                if len(serials) == 0:
                    print("No KST101 controller found.")
                    raise RuntimeError('No KST101 controller found')
                self._motor_ctrl = tlkt.Thorlabs.KST101(serials[0])
                if (self._motor_ctrl._CheckConnection() == False):
                    print("Connection with motor controller failed.")
                    raise RuntimeError('Connection with motor controller failed.')
                self._motor_ctrl.set_stage('ZST25')
        elif self._model == MotionController.SupportedDevices[1]:
            if dummy:
                self._motor_ctrl = mp789.MP_789A_4_DUMMY(man_port)
                pass
            else:
                self._motor_ctrl = mp789.MP_789A_4(man_port)
        elif self._model.startswith('MP_792_AXIS_'):
            self._motor_ctrl = parent
            self._axis = axis
            self._multi_axis = True
        else:
            print('Motion controller device model "%s" is not supported.'%(dev_model))
            raise Exception

        if self._motor_ctrl is None:
            raise RuntimeError('self.motor_ctrl is None')

        self._port = man_port

    # Setters.
    def set_limits(self, max_pos, min_pos):
        """Set the software-defined movement limits of this axis.

        Args:
            max_pos (_type_): _description_
            min_pos (_type_): _description_

        Returns:
            tuple[float, float]: _description_
        """
        self._max_pos = max_pos
        self._min_pos = min_pos

        return self._max_pos, self._min_pos

    # The number of steps per input value. Could be steps per millimeter, nanometer, or degree.
    def set_steps_per_value(self, steps) -> float:
        """Sets the conversion factor from hardware steps to real-world units.

        Args:
            steps (_type_): _description_

        Returns:
            float: _description_
        """
        if steps > 0:
            self._steps_per_value = steps

        return self._steps_per_value

    # Getters.
    def get_steps_per_value(self) -> float:
        """Gets the conversion factor from hardware steps to real-world units.

        Returns:
            float: _description_
        """
        return self._steps_per_value

    def is_dummy(self) -> bool:
        """Is this a dummy device? If False, it is real hardware.

        Returns:
            bool: _description_
        """
        return self.is_dummy

    # Commands.    
    def home(self, blocking: bool = False) -> None:
        """Sends a home command to the device. Optional blocking.

        Args:
            blocking (bool, optional): Whether to block or not; will spawn a thread if blocking is False. Defaults to False.
        """
        if self._homing:
            raise Exception("Already homing!")
        self._homing = True
        if blocking:
            self._home()
        else:
            self._homing_thread_active = True
            home_th = threading.Thread(target=self._home())
            home_th.start()

        return

    def _home(self) -> None:
        if self._multi_axis:
            self._motor_ctrl.home(self._axis)
        else:
            self._motor_ctrl.home()
        self._homing = False

    def get_position(self) -> float:
        """Returns the current position of the machine in real-world units.

        Returns:
            float: _description_
        """
        if self._steps_per_value == 0:
            return 0

        if self._multi_axis:
            return self._motor_ctrl.get_position(self._axis) / self._steps_per_value
        else:
            return self._motor_ctrl.get_position() / self._steps_per_value

    def is_homing(self) -> bool:
        """Returns whether the device is currently homing.

        Returns:
            bool: _description_
        """
        if self._multi_axis:
            return self._motor_ctrl.is_homing(self._axis)
        else:
            return self._motor_ctrl.is_homing()

    def is_moving(self) -> bool:
        if self._multi_axis:
            return self._motor_ctrl.is_moving(self._axis)
        else:
            return self._motor_ctrl.is_moving()

    def move_to(self, position, block):
        if self._moving:
            raise Exception("Already moving!")
        self._moving = True
        if block:
            return self._move_to(position, block)
        else:
            home_th = threading.Thread(target=self.home(), args=(position, block))
            home_th.start()
            return

    def _move_to(self, position, block):
        if self._steps_per_value == 0:
            raise Exception('Steps-per value has not been set for this axis. This value must be set in the Machine Configuration window.')
        if position > self._max_pos:
            raise Exception('Position is beyond the upper limit of this axis.')
        if position < self._min_pos:
            raise Exception('Position is beyond the lower limit of this axis.')

        if self._multi_axis:
            retval = self._motor_ctrl.move_to(position * self._steps_per_value, block, self._axis)
        else:
            retval = self._motor_ctrl.move_to(position * self._steps_per_value, block)

        self._moving = False
        return retval

    def port_name(self) -> str:
        return self._port

    def short_name(self) -> str:
        return self._motor_ctrl.short_name() + '_' + str(self._axis)

    def long_name(self) -> str:
        return self._motor_ctrl.long_name() + ' Axis ' + str(self._axis)

    pass


# Detector
# Genericizes the type of detector.
class Detector:
    SupportedDevices = ['KI 6485']

    def __init__(self, dummy: bool, dev_model: str, man_port: str = None):
        self.model = dev_model
        self.pa = None
        self._is_dummy = False

        if self.model == Detector.SupportedDevices[0]:
            if dummy:
                self.pa = ki_pico.KI_Picoammeter_Dummy(3)
                self._is_dummy = True
            else:
                if man_port is not None:
                    self.pa = ki_pico.KI_Picoammeter(3, man_port)
                else:
                    self.pa = ki_pico.KI_Picoammeter(3)
        else:
            print('Detector device model "%s" is not supported.'%(dev_model))
            raise Exception

    # TODO: Need a pinger to keep the ComPort open... here or in the drivers? Probably drivers.

    # Only function used in mmc.py (.pa.detect())
    def detect(self):
        # TODO: Fire out a trigger here.
        return self.pa.detect()

    def is_dummy(self):
        return self._is_dummy

    def short_name(self):
        return self.pa.short_name()

    def long_name(self):
        return self.pa.long_name()

    pass