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
    SIGNAL_update_main_axis_display = pyqtSignal(str)
    SIGNAL_qmsg_info = pyqtSignal(str, str)
    SIGNAL_qmsg_warn = pyqtSignal(str, str)
    SIGNAL_qmsg_crit = pyqtSignal(str, str)

    def __init__(self, parent: QMainWindow):
        super(UpdatePositionDisplays, self).__init__()
        self.other: MMC_Main = parent
        self.SIGNAL_update_main_axis_display.connect(self.other.update_position_displays)
        self.SIGNAL_qmsg_info.connect(self.other.QMessageBoxInformation)
        self.SIGNAL_qmsg_warn.connect(self.other.QMessageBoxWarning)
        self.SIGNAL_qmsg_crit.connect(self.other.QMessageBoxCritical)
        log.debug("Update worker init'd.")

    def run(self):
        log.debug("Update worker started.")
        def update():
            log.debug("Updating position displays...")
            self.other.current_position = self.other.motion_controllers.main_drive_axis.get_position()
            
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
                    self.other.disable_movement_sensitive_buttons(False)
                    self.other.homing_started = False
                    pass
            move_status = self.other.motion_controllers.main_drive_axis.is_moving()
            
            if not move_status and self.other.moving and not self.other.scanRunning:
                self.other.disable_movement_sensitive_buttons(False)

            self.other.moving = move_status
            self.other.previous_position = self.other.current_position

            self.SIGNAL_update_main_axis_display.emit('<b><i>%3.4f</i></b>'%(((self.other.current_position)) - self.other.zero_ofst))

        self.timer = QTimer()
        self.timer.timeout.connect(update)
        self.timer.start(1000)
        self.exec()