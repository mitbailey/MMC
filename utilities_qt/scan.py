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

import matplotlib
matplotlib.use('Qt5Agg')

from utilities import version
from utilities import log

class Scan(QThread):
    SIGNAL_status_update = pyqtSignal(str)
    SIGNAL_progress = pyqtSignal(int)
    SIGNAL_complete = pyqtSignal()

    SIGNAL_data_begin = pyqtSignal(int, dict) # scan index, which detector, redundant
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

    def __del__(self):
        self.wait()

    def run(self):
        # print('\n\n\n')
        self.other.disable_movement_sensitive_buttons(True)

        log.debug(self.other)
        log.info("Save to file? " + str(self.other.autosave_data_bool))

        self.SIGNAL_status_update.emit("PREPARING")
        sav_files = []
        tnow = dt.datetime.now()
        if (self.other.autosave_data_bool):
            log.info('Autosaving')
            filetime = tnow.strftime('%Y%m%d%H%M%S')
            for detector in self.other.detectors:
                filename = '%s%s_%s_data.csv'%(self.other.data_save_directory, filetime, detector.short_name())
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                sav_files.append(open(filename, 'w'))

        log.info("SCAN QTHREAD")
        log.info("Start | Stop | Step")
        log.info(self.other.startpos, self.other.stoppos, self.other.steppos)
        self.other.startpos = (self.other.UIE_mgw_start_qdsb.value())
        self.other.stoppos = (self.other.UIE_mgw_stop_qdsb.value())
        self.other.steppos = (self.other.UIE_mgw_step_qdsb.value())
        if self.other.steppos == 0 or self.other.startpos == self.other.stoppos:
            for f in sav_files:
                if (f is not None):
                    f.close()
            self.SIGNAL_complete.emit()
            return
        scanrange = np.arange(self.other.startpos, self.other.stoppos + self.other.steppos, self.other.steppos)
        nidx = len(scanrange)

        # MOVES TO ZERO PRIOR TO BEGINNING A SCAN
        self.SIGNAL_status_update.emit("ZEROING")
        # prep_pos = int((0 + self.other.zero_ofst))
        prep_pos = 0
        try:
            log.info('107: Moving to', prep_pos)
            self.other.motion_controllers.main_drive_axis.move_to(prep_pos, True)
            log.info('109: Done with', prep_pos)
        except Exception as e:
            log.error('Exception: Move Failyre - Main drive axis failed to move: %s'%(e))
            self.SIGNAL_error.emit('Move Failure', 'Main drive axis failed to move: %s'%(e))
            self.SIGNAL_complete.emit()
            return
        self.SIGNAL_status_update.emit("HOLDING")
        sleep(1)

        self._xdata = []
        self._ydata = []

        for detector in self.other.detectors:
            self._xdata.append([])
            self._ydata.append([])

        self._scan_id = self.other.table.scanId
        metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.main_drive_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': self.other.zero_ofst, 'scan_id': self.scanId}
        self.SIGNAL_data_begin.emit(self.scanId,  metadata) # emit scan ID so that the empty data can be appended and table scan ID can be incremented
        while self.scanId == self.other.table.scanId: # spin until that happens
            continue
        for idx, dpos in enumerate(scanrange):
            if not self.other.scanRunning:
                log.debug('scanRunning False, stop button may have been pressed (A).')
                break
            self.SIGNAL_status_update.emit("MOVING")
            
            try:
                log.info('138: Moving to', dpos)
                self.other.motion_controllers.main_drive_axis.move_to(dpos, True)
                log.info('140: Done with', dpos)
            except Exception as e:
                log.error('QMessageBox.Critical: Move Failure - Main drive axis failed to move: %s'%(e))
                QMessageBox.critical(self, 'Move Failure', 'Main drive axis failed to move: %s'%(e))
                pass
            pos = self.other.motion_controllers.main_drive_axis.get_position()
            self.SIGNAL_status_update.emit("SAMPLING")

            i=0
            for detector in self.other.detectors:
                buf = detector.detect()
                log.debug(buf)

                self.SIGNAL_progress.emit(round(((idx + 1) * 100 / nidx)/len(self.other.detectors)))

                if detector.short_name() == 'KI6485':
                    # process buf
                    words = buf.split(',') # split at comma
                    if len(words) != 3:
                        continue
                    try:
                        mes = float(words[0][:-1]) # skip the A (unit suffix)
                        err = int(float(words[2])) # skip timestamp
                    except Exception:
                        continue
                    mes = mes * 1e12 # convert to pA
                elif detector.short_name() == 'SR810':
                    mes = float(buf)
                else:
                    log.error('Unknown detector type.')
                    return

                self._xdata[i].append((((pos))))
                self._ydata[i].append(self.other.mes_sign * mes)
                self.SIGNAL_data_update.emit(self.scanId, i, self._xdata[i][-1], self._ydata[i][-1])

                log.debug(sav_files)
                if len(sav_files) > 0 and sav_files[i] is not None:
                    if idx == 0:
                        sav_files[i].write('# DATA RECORDED IN SOFTWARE VERSION: MMCv%s\n'%(version.__MMC_VERSION__))
                        sav_files[i].write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
                        sav_files[i].write('# Steps/mm: %f\n'%(self.other.motion_controllers.main_drive_axis.get_steps_per_value()))
                        sav_files[i].write('# mm/nm: %e; lambda_0 (nm): %e\n'%(0, self.other.zero_ofst))
                        sav_files[i].write('# Position (step),Position (nm),Mean Current(A),Status/Error Code\n')
                    # process buf
                    # 1. split by \n

                    buf = '%d,%e,%e,%d\n'%(pos, ((pos)) - self.other.zero_ofst, self.other.mes_sign * mes, err)
                    sav_files[i].write(buf)

                i += 1

        for sav_file in sav_files:
            if (sav_file is not None):
                sav_file.close()
        self.other.num_scans += 1

        self.SIGNAL_complete.emit()
        self.SIGNAL_data_complete.emit(self.scanId, 'main')
        log.debug('mainWindow reference in scan end: %d'%(sys.getrefcount(self.other) - 1))

    @property
    def xdata(self, which_detector: int):
        return np.array(self._xdata[which_detector], dtype=float)
    
    @property
    def ydata(self, which_detector: int):
        return np.array(self._ydata[which_detector], dtype=float)

    @property
    def scanId(self):
        return self._scan_id

class ScanSM(QThread):
    SIGNAL_status_update = pyqtSignal(str)
    SIGNAL_progress = pyqtSignal(int)
    SIGNAL_complete = pyqtSignal()

    SIGNAL_data_begin = pyqtSignal(int, dict) # scan index, which detector, redundant
    SIGNAL_data_update = pyqtSignal(int, int, float, float) # scan index, which detector, xdata, ydata (to be appended into index)
    SIGNAL_data_complete = pyqtSignal(int, str) # scan index, which detector, redundant

    SIGNAL_error = pyqtSignal(str, str)

    def __init__(self, parent: QMainWindow):
        super(ScanSM, self).__init__()
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

    def __del__(self):
        self.wait()

    def run(self):
        # Local variable setup.
        autosave_data = self.other.autosave_data_bool
        start = self.other.UIE_mgw_sm_start_set_qdsb.value()
        stop = self.other.UIE_mgw_sm_end_set_qdsb.value()
        step = self.other.UIE_mgw_sm_step_set_qdsb.value()
        scan_type = self.other.UIE_mgw_sm_scan_type_qcb.currentIndex()
        # 0 = Rotation
        # 1 = Translation
        # 2 = Theta2Theta (slaved detector axis) 


        # print('\n\n\n')
        self.other.disable_movement_sensitive_buttons(True)

        log.debug(self.other)
        log.info("Save to file? " + str(autosave_data))

        self.SIGNAL_status_update.emit("PREPARING")
        sav_files = []
        tnow = dt.datetime.now()
        if (autosave_data):
            log.info('Autosaving')
            filetime = tnow.strftime('%Y%m%d%H%M%S')
            for detector in self.other.detectors:
                filename = '%s%s_%s_data.csv'%(self.other.data_save_directory, filetime, detector.short_name())
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                sav_files.append(open(filename, 'w'))

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

        # MOVES TO ZERO PRIOR TO BEGINNING A SCAN
        self.SIGNAL_status_update.emit("ZEROING")
        prep_pos = 0

        if scan_type == 0: # Rotation
            try:
                log.info('273: Moving to', prep_pos)
                self.other.motion_controllers.sample_rotation_axis.move_to(prep_pos, True)
            except Exception as e:
                self.SIGNAL_error.emit('Move Failure', 'Sample rotation axis failed to move: %s'%(e))
                self.SIGNAL_complete.emit()
                return
            self.SIGNAL_status_update.emit('HOLDING')
            sleep(1)

            self._xdata = []
            self._ydata = []

            for detector in self.other.detectors:
                self._xdata.append([])
                self._ydata.append([])

            self._scan_id = self.other.table.scanId
            metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.sample_rotation_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': 0, 'scan_id': self.scanId}

            self.SIGNAL_data_begin.emit(self.scanId, metadata)
            while self.scanId == self.other.table.scanId:
                continue
            for idx, dpos in enumerate(scanrange):
                if not self.other.scanRunning:
                    log.debug('scanRunning False, stop button may have been pressed (B).')
                    break
                self.SIGNAL_status_update.emit('MOVING')
                try:
                    log.info('300: Moving to', dpos)
                    self.other.motion_controllers.sample_rotation_axis.move_to(dpos, True)
                except Exception as e:
                    self.SIGNAL_error.emit('Move Failure', 'Sample rotation axis failed to move: %s'%(e))
                    continue
                    pass
                
                pos = self.other.motion_controllers.sample_rotation_axis.get_position()
                
                self.SIGNAL_status_update.emit('SAMPLING')

                i=0
                for detector in self.other.detectors:
                    buf = detector.detect()
                    log.debug(buf)
                    self.SIGNAL_progress.emit(round(((idx + 1) * 100 / nidx)/len(self.other.detectors)))

                    words = buf.split(',')
                    if len(words) != 3:
                        continue
                    try:
                        mes = float(words[0][:-1])
                        err = int(float(words[2]))
                    except Exception:
                        continue

                    self._xdata[i].append(pos)
                    self._ydata[i].append(self.other.mes_sign * mes * 1e12)
                    self.SIGNAL_data_update.emit(self.scanId, i, self._xdata[i][-1], self._ydata[i][-1])

                    if len(sav_files) > 0 and sav_files[i] is not None:
                        if idx == 0:
                            sav_files[i].write('# DATA RECORDED IN SOFTWARE VERSION: MMCv%s\n'%(version.__MMC_VERSION__))
                            sav_files[i].write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
                            sav_files[i].write('# Steps/deg: %f\n'%(self.other.motion_controllers.sample_rotation_axis.get_steps_per_value()))
                            sav_files[i].write('# mm/nm: 0; lambda_0 (nm): 0\n')
                            sav_files[i].write('# Position (step),Position (nm),Mean Current(A),Status/Error Code\n')

                        buf = '%d,%e,%e,%d\n'%(pos, pos, self.other.mes_sign * mes, err)
                        sav_files[i].write(buf)

                    i += 1
            pass
        elif scan_type == 1: # Translation
            log.warn('Scan type 1 not implemented.')
            pass
        elif scan_type == 2: # Theta2Theta
            try:
                log.info('347: Moving to', prep_pos)
                self.other.motion_controllers.sample_rotation_axis.move_to(prep_pos, True)
            except Exception as e:
                self.SIGNAL_error.emit('Move Failure', 'Sample rotation axis failed to move: %s'%(e))
                self.SIGNAL_complete.emit()
                return
            try:
                log.info('354: Moving to', prep_pos)
                self.other.motion_controllers.detector_rotation_axis.move_to(prep_pos * 2, True)
            except Exception as e:
                self.SIGNAL_error.emit('Move Failure', 'Sample rotation axis failed to move: %s'%(e))
                self.SIGNAL_complete.emit()
                return
            self.SIGNAL_status_update.emit('HOLDING')
            sleep(1)

            self._xdata = []
            self._ydata = []

            for detector in self.other.detectors:
                self._xdata.append([])
                self._ydata.append([])

            self._scan_id = self.other.table.scanId
            metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.sample_rotation_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': 0, 'scan_id': self.scanId}

            self.SIGNAL_data_begin.emit(self.scanId, metadata)
            while self.scanId == self.other.table.scanId:
                continue
            for idx, dpos in enumerate(scanrange):
                if not self.other.scanRunning:
                    log.debug('scanRunning False, stop button may have been pressed (C).')
                    break
                self.SIGNAL_status_update.emit('MOVING')
                try:
                    log.info('381: Moving to', dpos)
                    self.other.motion_controllers.sample_rotation_axis.move_to(dpos, True)
                except Exception as e:
                    self.SIGNAL_error.emit('Move Failure', 'Sample rotation axis failed to move: %s'%(e))
                    continue
                    pass
                try:
                    log.info('388: Moving to', dpos)
                    self.other.motion_controllers.detector_rotation_axis.move_to(dpos * 2, True)
                except Exception as e:
                    self.SIGNAL_error.emit('Move Failure', 'Detector rotation axis failed to move: %s'%(e))
                    continue
                    pass
                
                pos = self.other.motion_controllers.sample_rotation_axis.get_position()
                
                self.SIGNAL_status_update.emit('SAMPLING')

                i=0
                for detector in self.other.detectors:
                    buf = detector.detect()
                    log.debug(buf)
                    self.SIGNAL_progress.emit(round(((idx + 1) * 100 / nidx)/len(self.other.detectors)))

                    words = buf.split(',')
                    if len(words) != 3:
                        continue
                    try:
                        mes = float(words[0][:-1])
                        err = int(float(words[2]))
                    except Exception:
                        continue

                    self._xdata[i].append(pos)
                    self._ydata[i].append(self.other.mes_sign * mes * 1e12)
                    self.SIGNAL_data_update.emit(self.scanId, i, self._xdata[i][-1], self._ydata[i][-1])

                    if len(sav_files) > 0 and sav_files[i] is not None:
                        if idx == 0:
                            sav_files[i].write('# DATA RECORDED IN SOFTWARE VERSION: MMCv%s\n'%(version.__MMC_VERSION__))
                            sav_files[i].write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
                            sav_files[i].write('# Steps/deg: %f\n'%(self.other.motion_controllers.sample_rotation_axis.get_steps_per_value()))
                            sav_files[i].write('# mm/nm: 0; lambda_0 (nm): 0\n')
                            sav_files[i].write('# Position (step),Position (nm),Mean Current(A),Status/Error Code\n')

                        buf = '%d,%e,%e,%d\n'%(pos, pos, self.other.mes_sign * mes, err)
                        sav_files[i].write(buf)

                    i += 1
            pass
        else:
            log.error('Unknown scan type requested.')
            for f in sav_files:
                if (f is not None):
                    f.close()
            self.SIGNAL_complete.emit()
            return

        for sav_file in sav_files:
            if (sav_file is not None):
                sav_file.close()
        self.other.num_scans += 1

        self.SIGNAL_complete.emit()
        self.SIGNAL_data_complete.emit(self.scanId, 'sample')
        log.debug('mainWindow reference in scan end: %d'%(sys.getrefcount(self.other) - 1))

    @property
    def xdata(self, which_detector: int):
        return np.array(self._xdata[which_detector], dtype=float)
    
    @property
    def ydata(self, which_detector: int):
        return np.array(self._ydata[which_detector], dtype=float)

    @property
    def scanId(self):
        return self._scan_id

class ScanDM(QThread):
    SIGNAL_status_update = pyqtSignal(str)
    SIGNAL_progress = pyqtSignal(int)
    SIGNAL_complete = pyqtSignal()

    SIGNAL_data_begin = pyqtSignal(int, dict) # scan index, which detector, redundant
    SIGNAL_data_update = pyqtSignal(int, int, float, float) # scan index, which detector, xdata, ydata (to be appended into index)
    SIGNAL_data_complete = pyqtSignal(int, str) # scan index, which detector, redundant

    SIGNAL_error = pyqtSignal(str, str)

    def __init__(self, parent: QMainWindow):
        super(ScanDM, self).__init__()
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

    def __del__(self):
        self.wait()

    def run(self):
        # Local variable setup.
        autosave_data = self.other.autosave_data_bool
        start = self.other.UIE_mgw_dm_start_set_qdsb.value()
        stop = self.other.UIE_mgw_dm_end_set_qdsb.value()
        step = self.other.UIE_mgw_dm_step_set_qdsb.value()
        # 0 = Rotation
        # 1 = Translation
        # 2 = Theta2Theta (slaved detector axis) 


        # print('\n\n\n')
        self.other.disable_movement_sensitive_buttons(True)

        log.debug(self.other)
        log.info("Save to file? " + str(autosave_data))

        self.SIGNAL_status_update.emit("PREPARING")
        sav_files = []
        tnow = dt.datetime.now()
        if (autosave_data):
            log.info('Autosaving')
            filetime = tnow.strftime('%Y%m%d%H%M%S')
            for detector in self.other.detectors:
                filename = '%s%s_%s_data.csv'%(self.other.data_save_directory, filetime, detector.short_name())
                os.makedirs(os.path.dirname(filename), exist_ok=True)
                sav_files.append(open(filename, 'w'))

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

        # MOVES TO ZERO PRIOR TO BEGINNING A SCAN
        self.SIGNAL_status_update.emit("ZEROING")
        prep_pos = 0

        try:
            log.info('531: Moving to', prep_pos)
            self.other.motion_controllers.detector_rotation_axis.move_to(prep_pos, True)
        except Exception as e:
            self.SIGNAL_error.emit('Move Failure', 'Detector rotation axis failed to move: %s'%(e))
            self.SIGNAL_complete.emit()
            return
        self.SIGNAL_status_update.emit('HOLDING')
        sleep(1)

        self._xdata = []
        self._ydata = []

        for detector in self.other.detectors:
            self._xdata.append([])
            self._ydata.append([])

        self._scan_id = self.other.table.scanId
        metadata = {'tstamp': tnow, 'steps_per_value': self.other.motion_controllers.detector_rotation_axis.get_steps_per_value(), 'mm_per_nm': 0, 'lam_0': 0, 'scan_id': self.scanId}

        self.SIGNAL_data_begin.emit(self.scanId, metadata)
        while self.scanId == self.other.table.scanId:
            continue
        for idx, dpos in enumerate(scanrange):
            if not self.other.scanRunning:
                log.debug('scanRunning False, stop button may have been pressed (D).')
                break
            self.SIGNAL_status_update.emit('MOVING')
            try:
                log.info('549: Moving to', dpos)
                self.other.motion_controllers.detector_rotation_axis.move_to(dpos, True)
            except Exception as e:
                self.SIGNAL_error.emit('Move Failure', 'Detector rotation axis failed to move: %s'%(e))
                continue
                pass
            
            pos = self.other.motion_controllers.detector_rotation_axis.get_position()
            
            self.SIGNAL_status_update.emit('SAMPLING')

            i=0
            for detector in self.other.detectors:
                buf = detector.detect()
                log.info(buf)
                self.SIGNAL_progress.emit(round(((idx + 1) * 100 / nidx)/len(self.other.detectors)))

                words = buf.split(',')
                if len(words) != 3:
                    continue
                try:
                    mes = float(words[0][:-1])
                    err = int(float(words[2]))
                except Exception:
                    continue

                self._xdata[i].append(pos)
                self._ydata[i].append(self.other.mes_sign * mes * 1e12)
                self.SIGNAL_data_update.emit(self.scanId, i, self._xdata[i][-1], self._ydata[i][-1])

                if len(sav_files) > 0 and sav_files[i] is not None:
                    if idx == 0:
                        sav_files[i].write('# DATA RECORDED IN SOFTWARE VERSION: MMCv%s\n'%(version.__MMC_VERSION__))
                        sav_files[i].write('# %s\n'%(tnow.strftime('%Y-%m-%d %H:%M:%S')))
                        sav_files[i].write('# Steps/deg: %f\n'%(self.other.motion_controllers.detector_rotation_axis.get_steps_per_value()))
                        sav_files[i].write('# mm/nm: 0; lambda_0 (nm): 0\n')
                        sav_files[i].write('# Position (step),Position (nm),Mean Current(A),Status/Error Code\n')

                    buf = '%d,%e,%e,%d\n'%(pos, pos, self.other.mes_sign * mes, err)
                    sav_files[i].write(buf)

                i += 1

        for sav_file in sav_files:
            if (sav_file is not None):
                sav_file.close()
        self.other.num_scans += 1

        self.SIGNAL_complete.emit()
        self.SIGNAL_data_complete.emit(self.scanId, 'detector')
        log.debug('mainWindow reference in scan end: %d'%(sys.getrefcount(self.other) - 1))

    @property
    def xdata(self, which_detector: int):
        return np.array(self._xdata[which_detector], dtype=float)
    
    @property
    def ydata(self, which_detector: int):
        return np.array(self._ydata[which_detector], dtype=float)

    @property
    def scanId(self):
        return self._scan_id