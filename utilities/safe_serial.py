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
from utilities import log
# from _typeshed import ReadableBuffer

safe_ports = {}

# Likely unnecessary.
def safe_close(port):
    log.info('safe_close: Closing port:', port)
    port.close()

# The overall idea here is to implement one mutex lock per port. A direct call to SafeSerial would create an arbitrary number of locks per port. Calling this function ensures that only have one lock per port by returning the SafeSerial object in charge of the port if we already have one, or creating a new one if we do not.
def SafeSerial(port: str, baudrate: int, timeout: float = ...):
    if port not in safe_ports.keys():
        safe_ports[port] = _SafeSerial(port, baudrate, timeout)
    return safe_ports[port]

class _SafeSerial:
    READ_DELAY = 0.01
    READ_SIZE = 128

    def __init__(self, port: str, baudrate: int, timeout: float = ...):
        print('Creating SafeSerial on port:', port)

        retries = 0
        while True:
            try:
                self._s = serial.Serial(port=port, baudrate=baudrate, timeout=timeout)
                break
            except Exception as e:
                log.warn('Failed to create SafeSerial on port ', port, 'because error:', e)
                retries += 1         
                time.sleep(0.25)
                if retries > 10:
                    log.error('Failed to create SafeSerial on port ', port, 'after 10 retries. Last error was:', e)
                    return
                continue

        self._m = Lock()
        # if self._s.is_open:
        #     log.warn('Port is already open. Closing and reopening.')
        #     self._s.close()
        #     time.sleep(0.25)
        # self._s.open()

        log.debug('SafeSerial created on port:', port)

    def __del__(self):
        log.info('SafeSerial destructor called.')
        self._m.acquire()
        log.info('Destroying SafeSerial.')
        self._s.close()

    def close(self):
        log.info('SafeSerial close called.')
        self._m.acquire()
        log.info('Closing SafeSerial.')
        self._s.close()

    # Mutex-protected.
    # TODO: Delete this.
    def write(self, buf):
        self._m.acquire() 

        buf = buf + b'\r\n'

        log.info('SafeSerial Write:', buf)

        retval = self._s.write(buf)
        self._m.release()
        return retval

    # INTERNAL USE ONLY
    # Mutex pre-acquired.
    def _write(self, buf):
        buf = buf + b'\r\n'

        log.info('SafeSerial Write:', buf)

        retval = self._s.write(buf)
        return retval

    # Prefixed with a small delay.
    def read(self, size: int = READ_SIZE):
        self._m.acquire() 
        time.sleep(_SafeSerial.READ_DELAY)
        retval = self._s.read(size)
        log.info('Serial RX:', retval)
        self._m.release()

        log.info('SafeSerial Read:', retval)
        return retval

    # INTERNAL USE ONLY
    # Mutex pre-acquired.
    def _read(self, size: int = READ_SIZE):
        time.sleep(_SafeSerial.READ_DELAY)
        retval = self._s.read(size)
        log.info('Serial RX:', retval)

        log.info('SafeSerial Read:', retval)
        return retval
    
    def xfer(self, tx_buf, rx_buf_size: int = READ_SIZE, custom_delay: float = 0.1):
        delay = _SafeSerial.READ_DELAY
        if custom_delay > delay:
            delay = custom_delay

        self._m.acquire()

        log.info('Serial xfer called with TX:', tx_buf)

        for i, msg in enumerate(tx_buf):
            # self._s.write(msg)
            self._write(msg)
            log.info(f'Serial xfer TX[{i}]: {msg}')

            time.sleep(delay)
    
            # retval = self._s.read(rx_buf_size)
            retval = self._read(rx_buf_size)
            log.info('Serial xfer RX:', retval)

            time.sleep(delay)

        self._m.release()

        return retval

    def _lock_override(self):
        self._m.acquire()

    def _release_override(self):
        self._m.release()