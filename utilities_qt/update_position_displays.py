#
# @file update_position_displays.py
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

# PyQt Imports
from PyQt5.QtCore import (pyqtSignal, QThread)
from PyQt5.QtWidgets import (QMainWindow)
from PyQt5.QtCore import QTimer
from utilities import log

# More Standard Imports
import matplotlib
matplotlib.use('Qt5Agg')

class UpdatePositionDisplays(QThread):
    # SIGNAL_update_main_axis_display = pyqtSignal(str)
    SIGNAL_update_axes_info = pyqtSignal(float, bool, bool, float, bool, bool, float, bool, bool, float, bool, bool, float, bool, bool, float, bool, bool)
    SIGNAL_qmsg_info = pyqtSignal(str, str)
    SIGNAL_qmsg_warn = pyqtSignal(str, str)
    SIGNAL_qmsg_crit = pyqtSignal(str, str)


    def __init__(self, parent: QMainWindow, cadence = 200):
        log.debug("Update worker init called.")
        self.CADENCE = cadence
        super(UpdatePositionDisplays, self).__init__()
        self.other: MMC_Main = parent
        # self.SIGNAL_update_main_axis_display.connect(self.other.update_position_displays)
        self.SIGNAL_update_axes_info.connect(self.other.update_axes_info)
        self.SIGNAL_qmsg_info.connect(self.other.QMessageBoxInformation)
        self.SIGNAL_qmsg_warn.connect(self.other.QMessageBoxWarning)
        self.SIGNAL_qmsg_crit.connect(self.other.QMessageBoxCritical)
        log.debug("Update worker init'd.")

    def run(self):
        log.debug("Update worker started.")
        def update():
            mda_pos = -999
            mda_moving = False 
            mda_homing = False 
            fwa_pos = -999
            fwa_moving = False
            fwa_homing = False
            sra_pos = -999
            sra_moving = False
            sra_homing = False
            saa_pos = -999
            saa_moving = False
            saa_homing = False
            sta_pos = -999
            sta_moving = False
            sta_homing = False
            dra_pos = -999
            dra_moving = False
            dra_homing = False

            try:
                if self.other.motion_controllers.main_drive_axis is not None:
                    # if self.other.motion_controllers.main_drive_axis is None:
                    #     log.debug("Main drive axis not selected.")
                    #     return

                    # log.debug("Updating position displays...")
                    mda_pos = self.other.motion_controllers.main_drive_axis.get_position()
                    
                    if self.other.homing_started: # set this to True at __init__ because we are homing, and disable everything. same goes for 'Home' button
                        home_status = self.other.motion_controllers.main_drive_axis.is_homing() # explore possibility of replacing this with is_homed()

                        if home_status:
                            # Detect if the device is saying its homing, but its not actually moving.
                            if self.other.current_position == self.other.previous_position:
                                self.other.immobile_count += 1
                            if self.other.immobile_count >= 3:
                                self.other.motion_controllers.main_drive_axis.home()
                                self.other.immobile_count = 0

                        if not home_status:
                            # enable stuff here
                            log.debug(home_status)
                            self.other.immobile_count = 0
                            self.other.scan_status_update("IDLE")
                            # self.other.disable_movement_sensitive_buttons(False)
                            self.other.homing_started = False
                            pass
                    move_status = self.other.motion_controllers.main_drive_axis.is_moving()
                    
                    mda_moving = move_status or self.other.scanRunning

                    # if not move_status and self.other.moving and not self.other.scanRunning:
                        # mda_moving = False
                        # self.other.disable_movement_sensitive_buttons(False)

                    mda_homing = self.other.motion_controllers.main_drive_axis.is_homing()

                    # self.other.moving = move_status
                    self.other.previous_position = self.other.current_position

                    # mda_pos = '<b><i>%3.4f</i></b>'%(((self.other.current_position)) - self.other.zero_ofst)
                    # self.SIGNAL_update_main_axis_display.emit('<b><i>%3.4f</i></b>'%(((self.other.current_position)) - self.other.zero_ofst))
            except Exception as e:
                log.error(str(e))

            try:
                if self.other.motion_controllers.filter_wheel_axis is not None:
                    fwa_moving = self.other.motion_controllers.filter_wheel_axis.is_moving()
                    fwa_homing = self.other.motion_controllers.filter_wheel_axis.is_homing()
                    fwa_pos = self.other.motion_controllers.filter_wheel_axis.get_position()
            except Exception as e:
                log.error(str(e))

            try:
                if self.other.motion_controllers.sample_rotation_axis is not None:
                    sra_moving = self.other.motion_controllers.sample_rotation_axis.is_moving()
                    sra_homing = self.other.motion_controllers.sample_rotation_axis.is_homing()
                    sra_pos = self.other.motion_controllers.sample_rotation_axis.get_position()
            except Exception as e:
                log.error(str(e))

            try:
                if self.other.motion_controllers.sample_angle_axis is not None:
                    saa_moving = self.other.motion_controllers.sample_angle_axis.is_moving()
                    saa_homing = self.other.motion_controllers.sample_angle_axis.is_homing()
                    saa_pos = self.other.motion_controllers.sample_angle_axis.get_position()
            except Exception as e:
                log.error(str(e))
                    
            try:
                if self.other.motion_controllers.sample_translation_axis is not None:
                    sta_moving = self.other.motion_controllers.sample_translation_axis.is_moving()
                    sta_homing = self.other.motion_controllers.sample_translation_axis.is_homing()
                    sta_pos = self.other.motion_controllers.sample_translation_axis.get_position()
            except Exception as e:
                log.error(str(e))

            try:
                if self.other.motion_controllers.detector_rotation_axis is not None:
                    dra_moving = self.other.motion_controllers.detector_rotation_axis.is_moving()
                    dra_homing = self.other.motion_controllers.detector_rotation_axis.is_homing()
                    dra_pos = self.other.motion_controllers.detector_rotation_axis.get_position()
            except Exception as e:
                log.error(str(e))

            self.SIGNAL_update_axes_info.emit(mda_pos, mda_moving, mda_homing, fwa_pos, fwa_moving, fwa_homing, sra_pos, sra_moving, sra_homing, saa_pos, saa_moving, saa_homing, sta_pos, sta_moving, sta_homing, dra_pos, dra_moving, dra_homing)

        self.timer = QTimer()
        self.timer.timeout.connect(update)
        self.timer.start(self.CADENCE)
        self.exec()