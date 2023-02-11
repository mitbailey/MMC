#
# @file motion_controller_list.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Effectively a struct with each type of motion controller.
# @version See Git tags for version information.
# @date 2022.12.30
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

class MotionControllerList:
    def __init__(self):
        self.main_drive_axis = None
        self.filter_wheel_axis = None
        self.sample_rotation_axis = None
        self.sample_translation_axis = None
        self.detector_rotation_axis = None