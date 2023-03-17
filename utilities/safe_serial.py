#
# @file safe_serial.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Mutex-locked serial communications.
# @version See Git tags for version information.
# @date 2023.03.17
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

import time
import serial
from threading import Lock
from _typeshed import ReadableBuffer

safe_ports = {}

# The overall idea here is to implement one mutex lock per port. A direct call to SafeSerial would create an arbitrary number of locks per port. Calling this function ensures that only have one lock per port by returning the SafeSerial object in charge of the port if we already have one, or creating a new one if we do not.
def SafeSerial(port: str, baudrate: int, timeout: float = ...):
    if port not in safe_ports.keys():
        safe_ports[port] = _SafeSerial(port, baudrate, timeout)
    return safe_ports[port]

class _SafeSerial:
    READ_DELAY = 0.1
    READ_SIZE = 128

    def __init__(self, port: str, baudrate: int, timeout: float = ...):
        self._s = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
        self._m = Lock()

    # Mutex-protected.
    def write(self, buf: ReadableBuffer):
        self._m.acquire()
        retval = self._s.write(buf)
        self._m.release()
        return retval

    # Prefixed with a small delay.
    def read(self):
        time.sleep(_SafeSerial.READ_DELAY)
        retval = self._s.read(_SafeSerial.READ_SIZE)
        return retval
    
    def _lock_override(self):
        self._m.acquire()

    def _release_override(self):
        self._m.release()