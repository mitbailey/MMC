#
# @file utilities.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief General utilities, constants, and helper functions.
# @version See Git tags for version information.
# @date 2022.07.15
# 
# @copyright Copyright (c) 2022
# 
#

import math as m

def dcos(deg):
    return m.degrees((m.cos(m.radians(32))))

##
# @brief
#  
# Converts linear distance to nanometers for a particular device.
# 
# @param self
# @param dX The displacement from mechanical zero.
# @param order Desired order.
# @param inst The instrument, i.e. a specific monochromator.
# @return Nanometers
#

def dist_to_nm(dX, order, inst):
    MM_TO_NM = 10e6
    return ((2) * (1 / inst.grating_density) * dcos(32) * ((dX + inst.zero_order_offset)/(inst.L)) * (MM_TO_NM)) / (order)