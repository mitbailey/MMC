#
# @file movement.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Generic, device-independent, movement functions.
# @version See Git tags for version information.
# @date 2022.07.15
# 
# @copyright Copyright (c) 2022
# 
#

from collections import deque

# Generic motion controller class (i.e., KST-101 wrapper).
class MotionController:
    # Circular queue which keeps track of the last POS_LENGTH positions.
    POS_LENGTH = 10
    positions = deque([], maxlen=POS_LENGTH)
    
    # Initializes MotionController class.
    def __init__(self, controller_model):
        # 
        pass
    
    ##
    # @brief
    #  
    # Moves the device to a particular position.
    # 
    # @param self
    # @param position 
    # @return
    #
    def move_to(self, position):
        pass

