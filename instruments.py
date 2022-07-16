#
# @file instruments.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Contains the class information for instruments.
# @version See Git tags for version information.
# @date 2022.07.15
# 
# @copyright Copyright (c) 2022
# 
#

class Monochromator():
    L = 0.0
    angle = 0.0
    # TODO: Enable automatic per-device changing.
    # Describes at what mechanical position the zero order is located in millimeters.
    # For instance, if moving to x = 1mm is equivalent to 0nm, then zero_order_offset should be 1.
    zero_order_offset = 0.0 # 1.0 for new monochromator

    def __init__(self, L, angle, grating_density, zero_order_offset):
        self.L = L
        self.angle = angle
        self.zero_order_offset = zero_order_offset