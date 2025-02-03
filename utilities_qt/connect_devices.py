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
from utilities import log

class ConnectDevices(QThread):
    SIGNAL_complete = pyqtSignal(list, list)
    SIGNAL_failure = pyqtSignal()
    SIGNAL_status = pyqtSignal(str)
    SIGNAL_load_bar = pyqtSignal(int)
    SIGNAL_qmsg_info = pyqtSignal(str, str)
    SIGNAL_qmsg_warn = pyqtSignal(str, str)
    SIGNAL_qmsg_crit = pyqtSignal(str, str)

    def __init__(self, parent: QMainWindow):
        super(ConnectDevices, self).__init__()
        self.other: MMC_Main = parent
        self.SIGNAL_complete.connect(self.other._connect_devices)
        self.SIGNAL_failure.connect(self.other._connect_devices_failure_cleanup)
        self.SIGNAL_status.connect(self.other._connect_devices_status)
        self.SIGNAL_load_bar.connect(self.other._connect_devices_progress_anim)
        self.SIGNAL_qmsg_info.connect(self.other.QMessageBoxInformation)
        self.SIGNAL_qmsg_warn.connect(self.other.QMessageBoxWarning)
        self.SIGNAL_qmsg_crit.connect(self.other.QMessageBoxCritical)
        log.debug('mainWindow reference in scan init: %d'%(sys.getrefcount(self.other) - 1))
        self._last_scan = -1

    def run(self):
        log.debug("connect_devices")
        self.SIGNAL_status.emit('Beginning device connection.')
        
        self.dummy = self.other.dummy
        log.info("Dummy Mode: " + str(self.dummy))

        self.num_detectors = self.other.num_detectors
        self.num_motion_controllers = self.other.num_motion_controllers

        # Motion Controller and Detector initialization.
        # Note that, for now, the Keithley 6485 and KST101 are the defaults.
        detectors_connected = [False] * self.num_detectors
        mtn_ctrls_connected = [False] * self.num_motion_controllers

        self.detectors = [None] * self.num_detectors
        self.mtn_ctrls = []
        self.mtn_ctrls.append(None) # Add a blank to the start so it matches the drop-downs.

        log.info('Detectors: %d'%(self.num_detectors))
        log.info('Motion controllers: %d'%(self.num_motion_controllers))
        self.SIGNAL_status.emit('Detectors: %d; Motion controllers: %d'%(self.num_detectors, self.num_motion_controllers))

        load_increment = (10000 / (self.num_detectors + self.num_motion_controllers)) * 1.0
        load = load_increment
        self.SIGNAL_load_bar.emit(load)
        log.debug('load:', load)

        for i in range(self.num_detectors):
            log.info('Instantiation attempt for detector #%d.'%(i))
            self.SIGNAL_status.emit(f'Establishing connection to detector {i} of {self.num_detectors}.')
            try:
                if self.other.UIEL_dmw_detector_qcb[i].currentIndex() != 0:
                    log.info("Using manual port: %s"%(self.other.UIEL_dmw_detector_qcb[i].currentText().split(' ')[0]))
                    # self.SIGNAL_status.emit("Connecting and configuring detector #%d on port %s."%(i, self.other.UIEL_dmw_detector_qcb[i].currentText().split(' ')[0]))
                    self.SIGNAL_status.emit(f'Configuring motion controller {i} of {self.num_motion_controllers}.')
                    self.detectors[i] = Detector(self.dummy, self.other.UIEL_dmw_detector_model_qcb[i].currentText(), self.other.UIEL_dmw_detector_qcb[i].currentText().split(' ')[0])

            except Exception as e:
                log.error(e)
                log.error("Failed to find detector (%s)."%(e))
                self.SIGNAL_status.emit("Failed to find detector #%d (%s)."%(i, e))
                self.SIGNAL_qmsg_warn.emit('Connection Failure', 'Failed to find detector (%s).'%(e))
                self.detectors[i] = None
                detectors_connected[i] = False
                self.SIGNAL_failure.emit()
                return
            if self.detectors[i] is None:
                detectors_connected[i] = False
            else:
                detectors_connected[i] = True
                self.SIGNAL_status.emit(f'Connected to detector {i} of {self.num_detectors}.')

            load+=load_increment
            self.SIGNAL_load_bar.emit(load)
            log.debug('load:', load)

        # for i, combo in self.dm_detector_combos:
        for i in range(self.num_motion_controllers):
            log.info('Instantiation attempt for motion controller #%d.'%(i))
            self.SIGNAL_status.emit(f'Establishing connection to motion controller {i} of {self.num_motion_controllers}.')
            try:
                if self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentIndex() != 0:
                    log.info("Using manual port: %s"%(self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0]))
                    # self.SIGNAL_status.emit("Connecting and homing motion controller #%d on port %s."%(i, self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0]))
                    log.info(self.dummy, self.other.UIEL_dmw_mtn_ctrl_model_qcb[i].currentText(), self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0])
                    
                    log.debug('About to call new_motion_controller().')
                    self.SIGNAL_status.emit(f'Homing motion controller {i} of {self.num_motion_controllers}.')
                    new_mtn_ctrls = mw.new_motion_controller(self.dummy, self.other.UIEL_dmw_mtn_ctrl_model_qcb[i].currentText(), self.other.UIEL_dmw_mtn_ctrl_qcb[i].currentText().split(' ')[0])
                    
                    log.debug('new_motion_controller() returned.')
                    
                    for ctrlr in new_mtn_ctrls:
                        log.debug('New axis:', ctrlr)
                        self.mtn_ctrls.append(ctrlr)

            except Exception as e:
                log.error("Failed to find motion controller #%d (%s)."%(i,e))
                self.SIGNAL_status.emit("Failed to find motion controller (%s)."%(e))
                self.SIGNAL_qmsg_warn.emit('Connection Failure', 'Failed to find motion controller (%s).'%(e)) 
                self.mtn_ctrls[-1] = None
                mtn_ctrls_connected[i] = False
                self.SIGNAL_failure.emit()
                return
            if len(self.mtn_ctrls) == 0 or self.mtn_ctrls[-1] is None:
                mtn_ctrls_connected[i] = False
            else:
                mtn_ctrls_connected[i] = True
                self.SIGNAL_status.emit(f'Connected to motion controller {i} of {self.num_motion_controllers}.')

            load+=load_increment
            self.SIGNAL_load_bar.emit(load)
            log.debug('load:', load)

        log.info('detectors_connected:', detectors_connected)
        log.info('mtn_ctrls_connected:', mtn_ctrls_connected)
        self.SIGNAL_status.emit('Detectors connected: %d; Motion controllers connected: %d'%(len(detectors_connected), len(mtn_ctrls_connected)))

        self.other.detectors = self.detectors
        self.other.mtn_ctrls = self.mtn_ctrls
        self.SIGNAL_complete.emit(detectors_connected, mtn_ctrls_connected)