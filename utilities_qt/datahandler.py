#
# @file datahandler.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief 
# @version See Git tags for version information.
# @date 2025.07.16
# 
# @copyright Copyright (c) 2025
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

# May be worked into the larger program at a later date.

from typing import List
import uuid
from dataclasses import dataclass
from collections import namedtuple

# Detector numbers are 1 or greater.
# Scan numbers are 0 or greater.
ScanID = namedtuple('ScanID', ['detector_number', 'scan_number'])

# 
class DataHandler:
    def __init__(self):
        self.data: dict[(int, int), List[float]] = {}
        # A mapping from UUIDs to their detector_number, scan_number tuple.
        self.usid_scanid_map: dict[uuid.UUID, (int, int)] = {}
        self.scan_number_map: dict[int, int] = {}

    def _increment_scan_number(self, detector_number: int) -> int:
        if detector_number not in self.scan_number_map:
            self.scan_number_map[detector_number] = 0
        else:
            self.scan_number_map[detector_number] += 1
        return self.scan_number_map[detector_number]

    # Scanning function comes at us with a UUID. If its new, its a new scan and we start a new data set. Otherwise, we append to the existing data set.
    def push(self, usid: uuid.UUID, detector_number: int, datum: float):
        # If we have never seen this USID before, then we need to add it to our mapping.
        # Simply, this takes the burden of determining the scan number off of the scanning function.
        # For now, in this class, the USID can be used to find the scan. However, later on and 
        # elsewhere we will use ScanID (detector_number, scan_number) as the key.
        if usid not in self.usid_scanid_map:
            self.usid_scanid_map[usid] = (detector_number, self._increment_scan_number(detector_number))

        # Regardless, we always need to append our datum to the data.
        self.data[self.usid_scanid_map[usid]].append(datum)

    def get_data(self, scan_id: ScanID) -> List[float]:
        if scan_id not in self.data:
            return []
        return self.data[scan_id]
    
    def get_all_data(self, detector_number: int) -> List[float]:
        all_data = []
        for scan_id, data in self.data.items():
            if scan_id[0] == detector_number:
                all_data.append(data)
        return all_data