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
import serial
import threading

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

# %% Custom Imports
from drivers import _thorlabs_kst_advanced as tlkt
from drivers import ki_picoammeter as ki_pico
from drivers import mp_789a_4 as mp789
from drivers import mp_792 as mp792

from utilities import ports_finder

# Motion Controller Types
# 0 - KST101

# Data Sampler Types
# 0 - Picoammeter, Keithley

# TODO: Need to implement external triggers when certain actions occur. Should also consider adding a trigger-only faux 'device.'

#%%
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
                # print('Keithley 6485 detected!')
                s.close()
                return '(KI 6485)'
        
        s.close()
        return '(Unknown)'

def find_all_ports():
    return ports_finder.find_all_ports()

#%% MotionController
# Genericizes the type of motor controller.
class MotionController:
    SupportedDevices = ['TL KST101', 'MP 789A-4', 'MP 792']

    def __init__(self, dummy: bool, dev_model: str, man_port: str = None):
        # TODO: Come up with a proper way of setting the sampler_type, ie as an argument.
        self.model = dev_model
        self.mm_to_idx = 0
        self._is_dummy = False
        self.motor_ctrl = None
        self.port = None

        # Initializes our motor_ctrl stuff depending on what hardware we're using.
        if self.model == MotionController.SupportedDevices[0]:
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
        elif self.model == MotionController.SupportedDevices[1]:
            if dummy:
                # self.motor_ctrl = mp789.MP_789A_4_DUMMY(man_port)
                pass
            else:
                self.motor_ctrl = mp789.MP_789A_4(man_port)
        elif self.model == MotionController.SupportedDevices[2]:
            if dummy:
                # self.motor_ctrl = mp792.MP_792(man_port)
                pass
            else:
                self.motor_ctrl = mp792.MP_792(man_port)
        else:
            print('Motion controller device model "%s" is not supported.'%(dev_model))
            raise Exception

        if self.motor_ctrl is None:
            raise RuntimeError('self.motor_ctrl is None')
        self.mm_to_idx = self.motor_ctrl.mm_to_idx
        self.port = man_port

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

    def port_name(self):
        return self.port

    def short_name(self):
        return self.motor_ctrl.short_name()

    def long_name(self):
        return self.motor_ctrl.long_name()

    pass

#%% DataSampler
# Genericizes the type of data sampler.
class DataSampler:
    SupportedDevices = ['KI 6485']

    def __init__(self, dummy: bool, dev_model: str, man_port: str = None):
        # TODO: Come up with a proper way of setting the sampler_type, ie as an argument.
        self.model = dev_model
        self.pa = None
        self._is_dummy = False

        if self.model == DataSampler.SupportedDevices[0]:
            if dummy:
                self.pa = ki_pico.KI_Picoammeter_Dummy(3)
                self._is_dummy = True
            else:
                if man_port is not None:
                    self.pa = ki_pico.KI_Picoammeter(3, man_port)
                else:
                    self.pa = ki_pico.KI_Picoammeter(3)
        else:
            print('Data sampler device model "%s" is not supported.'%(dev_model))
            raise Exception

    # Only function used in mmc.py (.pa.sample_data())
    def sample_data(self):
        # TODO: Fire out a trigger here.
        return self.pa.sample_data()

    def is_dummy(self):
        return self._is_dummy

    def short_name(self):
        return self.pa.short_name()

    def long_name(self):
        return self.pa.long_name()

    pass