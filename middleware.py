#
# @file middleware.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Provides a layer of abstraction between the MMC GUI and the underlying hardware device drivers.
# @version See Git tags for version information.
# @date 2022.09.23
# 
# @copyright Copyright (c) 2022
# 
#

# %% OS and SYS Imports
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

# %% More Standard Imports
import configparser as confp
from email.charset import QP
from time import sleep
from io import TextIOWrapper
import math as m
import numpy as np
import datetime as dt

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# %% Custom Imports
from drivers import _thorlabs_kst_advanced as tlkt
from drivers import picoammeter as pico

# Motion Controller Types
# 0 - KST101

# Data Sampler Types
# 0 - Picoammeter, Keithley

#%% MotionController
# Genericizes the type of motor controller.
class MotionController:
    def __init__(self, dummy: bool = False):
        self.controller_type = 0
        self.mm_to_idx = 0
        self._is_dummy = False

        # Initializes our motor_ctrl stuff depending on what hardware we're using.
        if self.controller_type == 0:
            if dummy:
                serials = tlkt.Thorlabs.KSTDummy._ListDevices()
                self.motor_ctrl = tlkt.Thorlabs.KSTDummy(serials[0])
                self.motor_ctrl.set_stage('ZST25')
                self._is_dummy = True
            else:
                print("Trying...")
                serials = tlkt.Thorlabs.ListDevicesAny()
                print(serials)
                if len(serials) == 0:
                    print("No KST101 controller found.")
                    raise RuntimeError('No KST101 controller found')
                self.motor_ctrl = tlkt.Thorlabs.KST101(serials[0])
                if (self.motor_ctrl._CheckConnection() == False):
                    print("Connection with motor controller failed.")
                    raise RuntimeError('Connection with motor controller failed.')
                self.motor_ctrl.set_stage('ZST25')

        elif self.controller_type == 1: # Example for adding future controller hardware.
            print("Controller type 1 does not exist yet.")

        self.mm_to_idx = self.motor_ctrl.mm_to_idx

    def is_dummy(self):
        return self.is_dummy

    def home(self):
        return self.motor_ctrl.home()

    def get_position(self):
        return self.motor_ctrl.get_position()

    def is_homing(self):
        return self.motor_ctrl.is_homing()

    def is_moving(self):
        return self.motor_ctrl.is_moving()

    def move_to(self, position, block):
        return self.motor_ctrl.move_to(position, block)

    pass

#%% DataSampler
# Genericizes the type of data sampler.
class DataSampler:
    def __init__(self, dummy: bool = False, man_port: str = None):
        self.sampler_type = 0
        self.pa = None
        self._is_dummy = False

        if self.sampler_type == 0:
            if dummy:
                self.pa = pico.Picodummy(3)
                self._is_dummy = True
            else:
                if man_port is not None:
                    self.pa = pico.Picoammeter(3, man_port)
                else:
                    self.pa = pico.Picoammeter(3)
        elif self.sampler_type == 1: # Example for adding future controller hardware.
            print("Sampler type 1 does not exist yet.")

    # Only function used in mmc.py (.pa.sample_data())
    def sample_data(self):
        return self.pa.sample_data()

    def is_dummy(self):
        return self._is_dummy

    pass

#%% ColorWheel
class ColorWheel:
    pass