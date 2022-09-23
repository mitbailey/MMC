#
# @file middleware.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Provides a layer of abstraction between the MMC GUI and the underlying hardware devices.
# @version See Git tags for version information.
# @date 2022.09.23
# 
# @copyright Copyright (c) 2022
# 
#

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

# %% More Imports
import configparser as confp
from email.charset import QP
from time import sleep
import weakref
from io import TextIOWrapper

# import _thorlabs_kst_advanced as tlkt
from drivers import _thorlabs_kst_advanced as tlkt
import picoammeter as pico
import math as m
import os
import numpy as np
import datetime as dt

import matplotlib
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from utilities.config import load_config, save_config, reset_config
import webbrowser
from utilities.datatable import DataTableWidget

# Motion Controller Types
# 0 - KST101

# Data Sampler Types
# 0 - Picoammeter, Keithley

# Genericizes the type of motor controller.
class MotionController:
    def __init__(self, n_args):
        self.controller_type = 0
        self.mm_to_idx = 0

        # Initializes our motor_ctrl stuff depending on what hardware we're using.
        if self.controller_type == 0:
            if n_args == 1:
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
            else:
                serials = tlkt.Thorlabs.KSTDummy._ListDevices()
                self.motor_ctrl = tlkt.Thorlabs.KSTDummy(serials[0])
                self.motor_ctrl.set_stage('ZST25')

        self.mm_to_idx = self.motor_ctrl.mm_to_idx

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

# Genericizes the type of data sampler.
class DataSampler:
    def __init__(self, n_args):
        self.sampler_type = 0
        self.pa = None

        if self.sampler_type == 0:
            if n_args != 1:
                self.pa = pico.Picodummy(3)
            else:
                self.pa = pico.Picoammeter(3)

    # Only function used in mmc.py (.pa.sample_data())
    def sample_data(self):
        return self.pa.sample_data()

    pass

# TBD
class ColorWheel:
    pass