#
# @file motion_controller_list.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Effectively a struct with each type of motion controller.
# @version See Git tags for version information.
# @date 2022.12.30
# 
# @copyright Copyright (c) 2022
# 
#

class MotionControllerList:
    def __init__(self):
        self.main_drive_axis = None
        self.filter_wheel_axis = None
        self.sample_rotation_axis = None
        self.sample_translation_axis = None
        self.detector_rotation_axis = None