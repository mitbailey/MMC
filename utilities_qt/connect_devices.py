#
# @file connect_devices.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief 
# @version See Git tags for version information.
# @date 2023.02.1
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

# PyQt Imports
from PyQt5.QtCore import (pyqtSignal, QThread)
from PyQt5.QtWidgets import (QMainWindow)

# More Standard Imports
import matplotlib
matplotlib.use('Qt5Agg')

# Custom Imports
import middleware as mw
from middleware import Detector

class ConnectDevices(QThread):
    SIGNAL_complete = pyqtSignal(list, list)
    SIGNAL_failure = pyqtSignal()
    SIGNAL_load_bar = pyqtSignal(int)
    SIGNAL_qmsg_info = pyqtSignal(str, str)
    SIGNAL_qmsg_warn = pyqtSignal(str, str)
    SIGNAL_qmsg_crit = pyqtSignal(str, str)

    def __init__(self, parent: QMainWindow):
        super(ConnectDevices, self).__init__()
        self.other: MMC_Main = parent
        self.SIGNAL_complete.connect(self.other._connect_devices)
        self.SIGNAL_failure.connect(self.other._connect_devices_failure_cleanup)
        self.SIGNAL_load_bar.connect(self.other._connect_devices_progress_anim)
        self.SIGNAL_qmsg_info.connect(self.other.QMessageBoxInformation)
        self.SIGNAL_qmsg_warn.connect(self.other.QMessageBoxWarning)
        self.SIGNAL_qmsg_crit.connect(self.other.QMessageBoxCritical)
        print('mainWindow reference in scan init: %d'%(sys.getrefcount(self.other) - 1))
        self._last_scan = -1

    def run(self):
        print('\n\n')
        print("connect_devices")

        self.dummy = self.other.dummy
        print("Dummy Mode: " + str(self.dummy))

        self.num_detectors = self.other.num_detectors
        self.num_motion_controllers = self.other.num_motion_controllers

        # Motion Controller and Detector initialization.
        # Note that, for now, the Keithley 6485 and KST101 are the defaults.
        detectors_connected = [False] * self.num_detectors
        mtn_ctrls_connected = [False] * self.num_motion_controllers

        self.detectors = [None] * self.num_detectors
        self.mtn_ctrls = []

        print('Detectors: %d'%(self.num_detectors))
        print('Motion controllers: %d'%(self.num_motion_controllers))

        load_increment = (10000 / (self.num_detectors + self.num_motion_controllers - 1)) * 0.8
        load = 10
        self.SIGNAL_load_bar.emit(load)

        for i in range(self.num_detectors):
            print('Instantiation attempt for detector #%d.'%(i))
            try:
                if self.other.UIEL_dmw_detector_qcb[i].currentIndex() != 0:
                    print("Using manual port: %s"%(self.other.UIEL_dmw_detector_qcb[i].currentText().split(' ')[0]))
                    self.detectors[i] = Detector(self.dummy, self.other.UIEL_dmw_detector_model_qcb[i].currentText(), self.other.UIEL_dmw_detector_qcb[i].currentText().split(' ')[0])

            except Exception as e:
                print(e)
                print("Failed to find detector (%s)."%(e))
                self.SIGNAL_qmsg_warn.emit('Connection Failure', 'Failed to find detector (%s).'%(e))
                self.detectors[i] = None
                detectors_connected[i] = False
                self.SIGNAL_failure.emit()
                return
            if self.detectors[i] is None:
                detectors_connected[i] = False
            else:
                detectors_connected[i] = True

            load+=load_increment
            self.SIGNAL_load_bar.emit(load)

        # for i, combo in self.dm_detector_combos:
        for i in range(self.num_motion_controllers):
            print('Instantiation attempt for motion controller #%d.'%(i))
            try:
                if self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentIndex() != 0:
                    print("Using manual port: %s"%(self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0]))
                    print(self.dummy, self.other.UIEL_dmw_mtn_ctrl_model_qcb[i].currentText(), self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0])
                    new_mtn_ctrls = mw.new_motion_controller(self.dummy, self.other.UIEL_dmw_mtn_ctrl_model_qcb[i].currentText(), self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0])
                    for ctrlr in new_mtn_ctrls:
                        print('New axis:', ctrlr)
                        self.mtn_ctrls.append(ctrlr)

            except Exception as e:
                print("Failed to find motion controller (%s)."%(e))
                self.SIGNAL_qmsg_warn.emit('Connection Failure', 'Failed to find motion controller (%s).'%(e)) 
                self.mtn_ctrls[-1] = None
                mtn_ctrls_connected[i] = False
                self.SIGNAL_failure.emit()
                return
            if len(self.mtn_ctrls) == 0 or self.mtn_ctrls[-1] is None:
                mtn_ctrls_connected[i] = False
            else:
                mtn_ctrls_connected[i] = True

            load+=load_increment
            self.SIGNAL_load_bar.emit(load)

        print('detectors_connected:', detectors_connected)
        print('mtn_ctrls_connected:', mtn_ctrls_connected)

        self.other.detectors = self.detectors
        self.other.mtn_ctrls = self.mtn_ctrls
        self.SIGNAL_complete.emit(detectors_connected, mtn_ctrls_connected)