#
# @file scan.py
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
from PyQt5.QtWidgets import (QMainWindow, QMessageBox)

# More Standard Imports
from time import sleep
# import weakref
import numpy as np
import datetime as dt
# from functools import partial
from enum import Enum

import matplotlib
matplotlib.use('Qt5Agg')

from utilities import version
from utilities import log

class ScanAxis(Enum):
    MAIN = 0
    SAMPLE = 1
    DETECTOR = 2
    MULTI = 3

class SampleScanType(Enum):
    ROTATION = 0
    TRANSLATION = 1
    THETA2THETA = 2 

class Scan(QThread):
    SIGNAL_status_update = pyqtSignal(str)
    SIGNAL_progress = pyqtSignal(int)
    SIGNAL_complete = pyqtSignal()

    SIGNAL_data_begin = pyqtSignal(int, int, dict) # scan index, which detector, redundant
    SIGNAL_data_update = pyqtSignal(int, int, float, float) # scan index, which detector, xdata, ydata (to be appended into index)
    SIGNAL_data_complete = pyqtSignal(int, str) # scan index, which detector, redundant

    SIGNAL_error = pyqtSignal(str, str)

    def __init__(self, parent: QMainWindow):
        super(Scan, self).__init__()
        self.other: MMC_Main = parent
        self.SIGNAL_status_update.connect(self.other.scan_status_update)
        self.SIGNAL_progress.connect(self.other.scan_progress)
        self.SIGNAL_complete.connect(self.other.scan_complete)
        self.SIGNAL_data_begin.connect(self.other.scan_data_begin)
        self.SIGNAL_data_update.connect(self.other.scan_data_update)
        self.SIGNAL_data_complete.connect(self.other.scan_data_complete)
        self.SIGNAL_error.connect(self.other.QMessageBoxCritical)
        log.debug('mainWindow reference in scan init: %d'%(sys.getrefcount(self.other) - 1))
        self._last_scan = -1
        self.ctrl_axis = ScanAxis.MAIN
        self.internal_scan_no = 0
        self.done = True

    def __del__(self):
        self.wait()

    def argstart(self, ctrl_axis: ScanAxis):
        self.ctrl_axis = ctrl_axis
        self.start()

    # def run(self, ctrl_axis: ScanAxis):
    def run(self):
        ctrl_axis = self.ctrl_axis

        which_detector = self.other.UIE_mgw_enabled_detectors_qcb.currentIndex()
        if which_detector == 0:
            active_detectors = self.other.detectors
        else:
            active_detectors = [self.other.detectors[which_detector - 1]]

        log.debug('self.other.detectors: %s'%(self.other.detectors))
        log.debug('active_detectors: %s'%(active_detectors))
        log.debug('which detector: %d'%(which_detector))
        log.debug('qcb index: %d'%(self.other.UIE_mgw_enabled_detectors_qcb.currentIndex()))

        log.warn('!!!')
    # def run(self):
        # print('\n\n\n')
        self.other.disable_movement_sensitive_buttons(True)
        log.warn('!!!')
        log.debug(self.other)
        log.info("Save to file? " + str(self.other.autosave_data_bool))
        log.warn('!!!')
        self.SIGNAL_status_update.emit("PREPARING")
        sav_files = []
        tnow = dt.datetime.now()
        if (self.other.autosave_data_bool):
            log.warn('!!!')
            log.info('Autosaving')
            filetime = tnow.strftime('%Y%m%d%H%M%S')

            for i, detector in enumerate(active_detectors):
                filename = '%s%s_%s_%d_data.csv'%(self.other.data_save_directory, filetime, detector.short_name(), i)
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                sav_files.append(open(filename, 'w'))

        log.warn('!!!')
        if ctrl_axis == ScanAxis.MAIN:
            log.warn('!!!')
            start = self.other.UIE_mgw_start_qdsb.value()
            stop = self.other.UIE_mgw_stop_qdsb.value()
            step = self.other.UIE_mgw_step_qdsb.value()
        elif ctrl_axis == ScanAxis.SAMPLE:
            start = self.other.UIE_mgw_sm_start_set_qdsb.value()
            stop = self.other.UIE_mgw_sm_end_set_qdsb.value()
            step = self.other.UIE_mgw_sm_step_set_qdsb.value()
        elif ctrl_axis == ScanAxis.DETECTOR:
            log.warn('!!!')
            start = self.other.UIE_mgw_dm_start_set_qdsb.value()
            stop = self.other.UIE_mgw_dm_end_set_qdsb.value()
            step = self.other.UIE_mgw_dm_step_set_qdsb.value()
        log.warn('!!!')

        log.info("SCAN QTHREAD")
        log.info("Start | Stop | Step")
        log.info(start, stop, step)

        if step == 0 or start == stop:
            for f in sav_files:
                if (f is not None):
                    f.close()
            self.SIGNAL_complete.emit()
            return
        scanrange = np.arange(start, stop + step, step)
        nidx = len(scanrange)

        scan_type = SampleScanType(self.other.UIE_mgw_sm_scan_type_qcb.currentIndex())

        # MOVES TO ZERO PRIOR TO BEGINNING A SCAN
        self.SIGNAL_status_update.emit("ZEROING")
        # prep_pos = int((0 + self.other.zero_ofst))

        prep_pos = 0
        try:
            log.info('107: Moving to', prep_pos)

            log.debug('ctrl_axis: %s'%(ctrl_axis))
            log.debug('scan_type: %s'%(scan_type))

            if ctrl_axis == ScanAxis.MAIN:
                log.info('ctrl_axis == ScanAxis.MAIN')
                self.other.motion_controllers.main_drive_axis.move_to(prep_pos, True)
                log.info('Complete move command.')
            elif ctrl_axis == ScanAxis.SAMPLE:
                log.info('ctrl_axis == ScanAxis.SAMPLE')
                if scan_type == SampleScanType.ROTATION:
                    log.info('scan_type == SampleScanType.ROTATION')
                    self.other.motion_controllers.sample_rotation_axis.move_to(prep_pos, True)
                elif scan_type == SampleScanType.TRANSLATION:
                    log.info('scan_type == SampleScanType.TRANSLATION')
                    self.other.motion_controllers.sample_translation_axis.move_to(prep_pos, True)
                elif scan_type == SampleScanType.THETA2THETA:
                    log.info('scan_type == SampleScanType.THETA2THETA')
                    self.other.motion_controllers.sample_rotation_axis.move_to(prep_pos, True)
                    self.other.motion_controllers.detector_rotation_axis.move_to(prep_pos * 2, True)
                else:
                    log.error(f'Invalid scan type for control axis: sample ({ctrl_axis}; {scan_type}).')
            elif ctrl_axis == ScanAxis.DETECTOR:
                log.info('ctrl_axis == ScanAxis.DETECTOR')
                self.other.motion_controllers.detector_rotation_axis.move_to(prep_pos, True)
            else:
                log.error(f'Invalid control axis ({ctrl_axis}; {scan_type}).')

            log.info('109: Done with', prep_pos)
        except Exception as e:
            log.error('Exception: Move Failure - Axis failed to move: %s'%(e))
            self.SIGNAL_error.emit('Move Failure', 'Axis failed to move: %s'%(e))
            self.SIGNAL_complete.emit()
            return
        
        log.info('Holding for 1 second.')

        self.SIGNAL_status_update.emit("HOLDING")
        sleep(1)

        log.info('Held for 1 second.')

        self._xdata = []
        self._ydata = []

        log.info('Creating data arrays for detectors.')

        for detector in active_detectors:
            self._xdata.append([])
            self._ydata.append([])

        log.info('Getting scan ID.')

        # self._scan_id = self.other.table_list[0].scanId
        # self._scan_id = self.other.global_scan_id
        self.last_global_scan_id = self.other.global_scan_id

        log.info('Global Scan ID:', self.other.global_scan_id)
        log.info('Internal Scan No:', self.internal_scan_no)

        if ctrl_axis == ScanAxis.MAIN:
            metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.main_drive_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': self.other.zero_ofst, 'scan_id': self.last_global_scan_id}
        elif ctrl_axis == ScanAxis.SAMPLE:
            if scan_type == SampleScanType.ROTATION:
                metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.sample_rotation_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': self.other.zero_ofst, 'scan_id': self.last_global_scan_id}
            elif scan_type == SampleScanType.TRANSLATION:
                metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.sample_translation_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': self.other.zero_ofst, 'scan_id': self.last_global_scan_id}
            elif scan_type == SampleScanType.THETA2THETA:
                metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.sample_rotation_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': self.other.zero_ofst, 'scan_id': self.last_global_scan_id}
            else:
                log.error(f'Invalid scan type for control axis: sample ({ctrl_axis}; {scan_type}).')
        elif ctrl_axis == ScanAxis.DETECTOR:
            metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.detector_rotation_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': self.other.zero_ofst, 'scan_id': self.last_global_scan_id}
        else:
            log.error(f'Invalid control axis ({ctrl_axis}; {scan_type}).')

        log.info('Emitting data begin signal.')

        # This ensures that the 'i' is the index of the detector in the Main GUI's list, not just always 0 if we only have one active detector.
        for i, det in enumerate(self.other.detectors):
            if det in active_detectors:
                self.SIGNAL_data_begin.emit(i, self.last_global_scan_id, metadata)

        # log.info('Waiting for scan ID to change.')

        # while self.scanId == self.other.table_list[0].scanId: # spin until that happens
        #     continue
        for idx, dpos in enumerate(scanrange):
            log.warn('!!! STARTING SCAN LOOP SECTION')
            log.warn('!!! STARTING SCAN LOOP SECTION')
            log.warn('!!! STARTING SCAN LOOP SECTION')

            if not self.other.scanRunning:
                log.debug('scanRunning False, stop button may have been pressed (A).')
                break
            self.SIGNAL_status_update.emit("MOVING")
            
            try:
                log.info('138: Moving to', dpos)
                log.warn('!!! MOVING TO')
                log.warn('!!! MOVING TO')
                log.warn('!!! MOVING TO')
                if ctrl_axis == ScanAxis.MAIN:
                    self.other.motion_controllers.main_drive_axis.move_to(dpos, True)
                elif ctrl_axis == ScanAxis.SAMPLE:
                    if scan_type == SampleScanType.ROTATION:
                        self.other.motion_controllers.sample_rotation_axis.move_to(dpos, True)
                    elif scan_type == SampleScanType.TRANSLATION:
                        self.other.motion_controllers.sample_translation_axis.move_to(dpos, True)
                    elif scan_type == SampleScanType.THETA2THETA:
                        self.other.motion_controllers.sample_rotation_axis.move_to(dpos, True)
                        self.other.motion_controllers.detector_rotation_axis.move_to(dpos * 2, True)
                elif ctrl_axis == ScanAxis.DETECTOR:
                    self.other.motion_controllers.detector_rotation_axis.move_to(dpos, True)
                
                log.warn('!!! DONE MOVING TO')
                log.warn('!!! DONE MOVING TO')
                log.warn('!!! DONE MOVING TO')

                log.info('140: Done with', dpos)
            except Exception as e:
                log.error('QMessageBox.Critical: Move Failure - Axis failed to move: %s'%(e))
                self.SIGNAL_error.emit('Move Failure', 'Axis failed to move: %s'%(e))
                break
            log.debug("Getting axis position.")

            log.warn('!!! GETTING POSITION')
            log.warn('!!! GETTING POSITION')
            log.warn('!!! GETTING POSITION')

            if ctrl_axis == ScanAxis.MAIN:
                pos = self.other.motion_controllers.main_drive_axis.get_position()
            elif ctrl_axis == ScanAxis.SAMPLE:
                if scan_type == SampleScanType.ROTATION:
                    pos = self.other.motion_controllers.sample_rotation_axis.get_position()
                elif scan_type == SampleScanType.TRANSLATION:
                    pos = self.other.motion_controllers.sample_translation_axis.get_position()
                elif scan_type == SampleScanType.THETA2THETA:
                    pos = self.other.motion_controllers.sample_rotation_axis.get_position()
                    det_pos = self.other.motion_controllers.detector_rotation_axis.get_position()
            elif ctrl_axis == ScanAxis.DETECTOR:
                pos = self.other.motion_controllers.detector_rotation_axis.get_position()

            log.warn('!!! DONE GETTING POSITION')
            log.warn('!!! DONE GETTING POSITION')
            log.warn('!!! DONE GETTING POSITION')

            log.debug("Emitting status update signal SAMPLING.")
            self.SIGNAL_status_update.emit("SAMPLING")

            i=0
            log.debug("Beginning loop.")
            for i, detector in enumerate(active_detectors):
                mes = detector.detect()
                log.debug(mes)

                self.SIGNAL_progress.emit(round(((idx + 1) * 100 / nidx)/len(active_detectors)))
                
                log.debug("Appending data.")
                if (i != 0) and (ctrl_axis == ScanAxis.SAMPLE) and (scan_type == SampleScanType.THETA2THETA):
                    log.debug(f"Appending detector position {det_pos}")
                    self._xdata[i].append((((det_pos))))
                else:
                    log.debug(f"Appending position {pos}")
                    self._xdata[i].append((((pos))))
                self._ydata[i].append(self.other.mes_sign * mes)
                log.debug(f'_ydata[i][-1]: {self._ydata[i][-1]}')
                self.SIGNAL_data_update.emit(self.last_global_scan_id, i, self._xdata[i][-1], self._ydata[i][-1])

                log.debug(sav_files)
                if len(sav_files) > 0 and sav_files[i] is not None:
                    if idx == 0:
                        log.debug(f"Save files [{i}]")
                        sav_files[i].write('# DATA RECORDED IN SOFTWARE VERSION: %sv%s\n'%(version.__short_name__, version.__version__))
                        sav_files[i].write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))

                        if ctrl_axis == ScanAxis.MAIN:
                            sav_files[i].write('# Steps/mm: %f\n'%(self.other.motion_controllers.main_drive_axis.get_steps_per_value()))
                        elif ctrl_axis == ScanAxis.SAMPLE:
                            if scan_type == SampleScanType.ROTATION:
                                sav_files[i].write('# Steps/mm: %f\n'%(self.other.motion_controllers.sample_rotation_axis.get_steps_per_value()))
                            elif scan_type == SampleScanType.TRANSLATION:
                                sav_files[i].write('# Steps/mm: %f\n'%(self.other.motion_controllers.sample_translation_axis.get_steps_per_value()))
                            elif scan_type == SampleScanType.THETA2THETA:
                                sav_files[i].write('# Steps/mm: %f\n'%(self.other.motion_controllers.sample_rotation_axis.get_steps_per_value()))
                        elif ctrl_axis == ScanAxis.DETECTOR:
                            sav_files[i].write('# Steps/mm: %f\n'%(self.other.motion_controllers.detector_rotation_axis.get_steps_per_value()))
                        
                        sav_files[i].write('# mm/nm: %e; lambda_0 (nm): %e\n'%(0, self.other.zero_ofst))
                        sav_files[i].write('# Position (step),Position (nm),Mean Current(A),Status/Error Code\n')
                    # process buf
                    # 1. split by \n

                    buf = '%d,%e,%e\n'%(pos, ((pos)) - self.other.zero_ofst, self.other.mes_sign * mes)
                    sav_files[i].write(buf)

                i += 1

                log.warn('!!! DONE LOOP SECTION')
                log.warn('!!! DONE LOOP SECTION')
                log.warn('!!! DONE LOOP SECTION')

        for sav_file in sav_files:
            if (sav_file is not None):
                sav_file.close()
        self.other.num_scans += 1

        self.SIGNAL_complete.emit()
        self.SIGNAL_data_complete.emit(self.last_global_scan_id, 'main')
        log.debug('mainWindow reference in scan end: %d'%(sys.getrefcount(self.other) - 1))

        self.done = True

    @property
    def xdata(self, which_detector: int):
        return np.array(self._xdata[which_detector], dtype=float)
    
    @property
    def ydata(self, which_detector: int):
        return np.array(self._ydata[which_detector], dtype=float)

    # @property
    # def scanId(self):
    #     return self.last_global_scan_id

class QueueExecutor(QThread):
    def __init__(self, parent: QMainWindow):
        super(QueueExecutor, self).__init__()
        self.other: MMC_Main = parent
        self._queue = []
        self._running = False

    def set_scan_obj(self, scan_obj: Scan):
        self._scan_obj = scan_obj

    def set_queue(self, queue: list):
        self._queue = queue

    def run(self):
        log.info('QueueExecutor - Beginning processing of the following queue: %s'%(self._queue))

        for cmd in self._queue:
            log.info('QueueExecutor - Processing command: %s'%(cmd))

            args = cmd.split(' ')

            if cmd.startswith('#') or cmd == '':
                log.info('QueueExecutor - Skipping comment or empty line.')
                continue

            if args[0] == 'RUN':
                if args[1] == 'MDA':
                    log.info('QueueExecutor - Running MDA scan.')
                    self.other.scan.ctrl_axis = ScanAxis.MAIN
                    # TODO: which detector
                    self.other.UIE_mgw_start_qdsb.setValue(float(args[2]))
                    self.other.UIE_mgw_stop_qdsb.setValue(float(args[3]))
                    self.other.UIE_mgw_step_qdsb.setValue(float(args[4]))

                    self.other.scan.done = False

                    self.other.scan.start()

                    while not self.other.scan.done:
                        sleep(0.1)
                else:
                    log.error('QueueExecutor - Unknown scan type: %s'%(args[1]))

            elif args[0] == 'WAIT':
                sleep(float(args[1]))
            else:
                log.error('QueueExecutor - Unknown command argument: %s'%(args[0]))

        pass

class ScanType(Enum):
    ROTATION = 0
    TRANSLATION = 1
    THETA2THETA = 2 