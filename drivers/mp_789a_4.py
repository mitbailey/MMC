#
# @file mp_789a_4.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Driver for the McPherson Model 789A-4 Scan Controller.
# @version See Git tags for version information.
# @date 2022.11.04
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

# import serial
from __future__ import annotations
import threading
import time
from utilities import ports_finder
from utilities import safe_serial
from threading import Lock
from utilities import log

from .stagedevice import StageDevice

class MP_789A_4(StageDevice):
    WR_DLY = 0.05
    HSM = 4

    def backend(self)->str:
        return 'MP_789A_4'

    def __init__(self, port):
        """ MP_789A_4 constructor.

        Args:
            port (_type_): The port on which to attempt a connection.

        Raises:
            RuntimeError: Raised if `port` is NoneType.
            RuntimeError: Raised if `port` is not found in the list of available ports; may already be in use.
            RuntimeError: Raised if the serial ID request response times out.
            RuntimeError: Raised if the serial ID request response is invalid. 
            RuntimeError: Raised is the SafeSerial object is NoneType.
        """

        # Default values for the class.
        self.s_name = 'MP789'
        self.l_name = 'McPherson 789A-4'
        self._homing = False
        self._moving = False
        self.moving_poll_mutex = Lock()
        self._backlash_lock = False
        self.stop_queued = 0
        self._position = 0

        log.info('Attempting to connect to McPherson Model 789A-4 Scan Controller on port %s.'%(port))

        # Check if we were given a port.
        if port is None:
            log.error('Port is none type.')
            raise RuntimeError('Port is none type.')
        
        # Check if the port is available.
        ser_ports = ports_finder.find_serial_ports()
        if port not in ser_ports:
            log.error('Port not valid. Is another program using the port?')
            raise RuntimeError('Port not valid. Is another program using the port?')

        # Get a SafeSerial connection on the port and begin communication.
        self.s = safe_serial.SafeSerial(port, 9600, timeout=0.3)

        # self.s.write(b' ')
        # time.sleep(MP_789A_4.WR_DLY)
        # rx = self.s.read(128)#.decode('utf-8').rstrip()

        rx = self.s.xfer([b' '])

        log.debug(rx)

        # Check the response to ensure connection to a 789A-4.
        if rx is None or rx == b'':
            raise RuntimeError('Response timed out.')
        elif rx == b' v2.55\r\n#\r\n':
            log.info('McPherson model 789A-4 Scan Controller found.')
        elif rx == b' #\r\n':
            log.info('McPherson model 789A-4 Scan Controller already initialized.')
        else:
            raise RuntimeError('Invalid response.')

        if self.s is None:
            raise RuntimeError('self.s is None')

        # Starting movement watchdog.
        self.movement_status_tid = threading.Thread(target=self.movement_status_thread)
        self.movement_status_tid.start()

        # Home the 789A-4.
        self.home()

    def movement_status_thread(self):
        # This thread runs in the background.
        # It will be the only thing which calls the internal _is_moving() function.
        # The middleware calls the external is_moving() function.
        # This way we can ensure that the device is only queried for movement status when it is safe to do so.

        while True:
            time.sleep(0.25)

            axis_moving = self._moving

            if axis_moving:
                # Check if the backlash lock is active. If so, we should check again later.
                if self._backlash_lock:
                    # log.info('Backlash lock is active. Skipping movement inquiry.')
                    log.info('Backlash lock is active, but not skipping movement inquiry.')

                    # continue

                # Update the movement status of the axis which is moving.
                log.info('Checking movement status of axis.')
                self._moving = self._is_moving()
                log.info(f'Axis is moving? {self._moving}.')

            # Checking for movement in this last case isn't necessary because we know when we initiate an axis move - it should be set to True (moving) when its told to move. The assumption should be that it does begin to move. Then, we use the previous case to prove it isn't moving once its stopped (or failed to start moving).
            elif not axis_moving:
                # Update the movement status of all alive axes, since none are reported as moving.
                log.info('Axis has not been marked or reported as moving. Skipping movement inquiry.')

    def set_stage(self, stage):
        pass

    def get_stage(self):
        return None

    def home(self)->bool:
        """ Homes the 789A-4.

        Raises:
            RuntimeError: Raised if the device hits an edge limit-switch before a home switch; may not have a home switch.
            RuntimeError: Raised if the device hits an edge limit-switch before a home switch; may not have a home switch.
            RuntimeError: Raised when the device attempts to home from a location which it is unable to home from.

        Returns:
            bool: Success (True) or failure (False).
        """

        # Halt the device before beginning the homing process.
        self.stop()

        # Set the `_is_homing` flag to disallow simultaneous homing attempts.
        log.info('Beginning home.')
        self._homing = True

        # Enable the 789A-4's homing circuit.
        # self.s.write(b'A8')
        # time.sleep(MP_789A_4.WR_DLY)
        # rx = self.s.read(128).decode('utf-8')

        rx = self.s.xfer([b'A8']).decode('utf-8')

        # Check limit switch status.
        # self.s.write(b']')
        # time.sleep(MP_789A_4.WR_DLY)
        # rx_raw = self.s.read(128)
        rx_raw = self.s.xfer([b']'])
        rx = rx_raw.decode('utf-8')

        log.debug('RECEIVED (raw):', rx_raw)

        # Carries out the 789A-4 homing algorithm as described in the relevant manual.
        if (('32' in rx) or ('128' in rx)) and ('+' not in rx and '-' not in rx):
            log.info('Home switch blocked.')

            # Home switch blocked.
            # Move at constant velocity (23 KHz).
            # self.s.write(b'M+23000')
            self.s.xfer([b'M+23000'])

            # time.sleep(MP_789A_4.WR_DLY)
            while True:
                # Check limit status - send every 0.8 seconds.
                # self.s.write(b']')
                # time.sleep(MP_789A_4.WR_DLY)     
                # rx = self.s.read(128).decode('utf-8')
                rx = self.s.xfer([b']']).decode('utf-8')
                if ('0' in rx or '2' in rx) and ('+' not in rx and '-' not in rx): # Not-on-a-limit-switch status is 0 when stationary, 2 when in motion.
                    break
                elif ('64' in rx or '128' in rx) and ('+' not in rx and '-' not in rx): # If we have hit either of the extreme limit switches and stopped.
                    log.error('Hit edge limit switch when homing. Does this device have a home sensor?')
                    raise RuntimeError('Hit edge limit switch when homing. Does this device have a home sensor?')
                time.sleep(MP_789A_4.WR_DLY * 7)
            # Soft stop when homing flag is located.
            # self.s.write(b'@')
            self.s.xfer([b'@'])
            time.sleep(2) 
            # Back into home switch 2 motor revolutions.
            self.s.xfer(b'-72000')
        # self.s.xfer([b'-108000'])
            time.sleep(2) 
            # Go 2 motor revolutions up.
            # self.s.write(b'+72000')
        # self.s.xfer([b'+72000'])
            # time.sleep(3) 
            # Enable 'high accuracy' circuit.
            # self.s.write(b'A24')
            self.s.xfer([b'A24'])
            # time.sleep(1) 
            # Find edge of home flag at 1000 steps/sec.
            # self.s.write(b'F1000,0')
            # sps = 1000 * MP_789A_4.HSM
            # msg = f'F{str(sps)},0'
            # self.s.xfer([msg.encode('utf-8')])
            self.s.xfer([b'F1000,0'])
            # time.sleep(5)

            while True:
                # Check limit status - send every 0.8 seconds.
                rx = self.s.xfer([b']']).decode('utf-8')
                if ('0' in rx or '32' in rx) and ('+' not in rx and '-' not in rx): # We're not moving one way or another.
                    break
                time.sleep(2)

            # Disable home circuit.
            # self.s.write(b'A0')
            self.s.xfer([b'A0'])
            time.sleep(MP_789A_4.WR_DLY) 
            pass
        elif ('0' in rx or '2' in rx or '64' in rx) and ('+' not in rx and '-' not in rx):
            # NOTE: When not on a limit switch, the device reports 0 when stationary and 2 when in motion. It seems sometimes it may report 2 even when not moving. We should just try to home anyway.
            if '2' in rx:
                log.warn('Device is moving. Will attempt to home anyway.')
            log.info('Home switch not blocked.')
            # Home switch not blocked.
            # Move at constant velocity (23 KHz).
            # self.s.write(b'M-23000')
            self.s.xfer([b'M-23000'])
            time.sleep(MP_789A_4.WR_DLY)
            while True:
                # Check limit status - send every 0.8 seconds.
                # self.s.write(b']')
                # time.sleep(MP_789A_4.WR_DLY)     
                # rx = self.s.read(128).decode('utf-8')
                rx = self.s.xfer([b']']).decode('utf-8')
                if ('32' in rx or '34' in rx) and ('+' not in rx and '-' not in rx): # Home-switch-blocked status is 32 when stationary, 34 when in motion.
                    break
                elif ('64' in rx or '128' in rx) and ('+' not in rx and '-' not in rx): # If we have hit either of the extreme limit switches and stopped.
                    # TODO: Some 789s don't have a limit switch. In this case, we will need to home using the lower limit switch... ?

                    log.error('Hit edge limit switches twice when homing. Does this device have a home sensor?')
                    raise RuntimeError('Hit edge limit switches twice when homing. Does this device have a home sensor?')
                time.sleep(MP_789A_4.WR_DLY * 7)
            # Soft stop when homing flag is located.
            # self.s.write(b'@')
            self.s.xfer([b'@'])
            time.sleep(2) 
            # Back into home switch 2 motor revolutions.
            self.s.xfer(b'-72000')
            time.sleep(2)
            # Back into home switch 3 motor revolutions.
            # self.s.write(b'-108000')
        # self.s.xfer([b'-108000'])
            # time.sleep(1) 
            # Go 2 motor revolutions up.
            # self.s.write(b'+72000')
        # self.s.xfer([b'+72000'])
            # time.sleep(1) 
            # Enable 'high accuracy' circuit.
            # self.s.write(b'A24')
            self.s.xfer([b'A24'])
            # time.sleep(1) 
            # Find edge of home flag at 1000 steps/sec.
            # self.s.write(b'F1000,0')

            # sps = 1000 * MP_789A_4.HSM
            # msg = f'F{str(sps)},0'
            # self.s.xfer([msg.encode('utf-8')])
            self.s.xfer([b'F1000,0'])
            # time.sleep(5) 

            while True:
                # Check limit status - send every 0.8 seconds.
                rx = self.s.xfer([b']']).decode('utf-8')
                if ('0' in rx or '32' in rx) and ('+' not in rx and '-' not in rx): # We're not moving one way or another.
                    break
                time.sleep(2)

            # Disable home circuit.
            # self.s.write(b'A0')
            self.s.xfer([b'A0'])
            time.sleep(MP_789A_4.WR_DLY) 
            pass
        else:
            log.error('Unknown position to home from.', rx)
            raise RuntimeError('Unknown position to home from (%s).'%(rx))

        self._moving = True # assume moving until we confirm not

        # The standard is for the device drivers to read 0 when homed if the controller does not itself provide a value.
        # It is up to the middleware to handle zero- and home-offsets.
        if (self._moving):
            log.warn('Post-home movement detected. Entering movement remediation.')
            # self.s.write(b'@')
            self.s.xfer([b'@'])
            time.sleep(MP_789A_4.WR_DLY * 10)
        stop_waits = 0
        
        while(self._moving):
            if stop_waits > 3:
                stop_waits = 0
                log.warn('Re-commanding that device ceases movement.')
                # self.s.write(b'@')
                self.s.xfer([b'@'])
            stop_waits += 1
            log.warn('Waiting for device to cease movement.')
            time.sleep(MP_789A_4.WR_DLY * 10)

        # Reset position and homing status.
        self._position = 0
        self._homing = False
        return True

    def get_position(self):
        """ Returns the current position of the 789A-4.

        Returns:
            _type_: The position.
        """

        log.debug('func: get_position')
        return self._position
    
    def stop(self):
        """ Triple-redundant serial stop command.
        """

        self.stop_queued = 1

        self.s.xfer([b'@'])
        # self.s.write(b'@')
        log.info('Stopping.')
        time.sleep(MP_789A_4.WR_DLY)

        self.s.xfer([b'@'])
        # self.s.write(b'@')
        log.info('Stopping.')
        time.sleep(MP_789A_4.WR_DLY)

        self.s.xfer([b'@'])
        # self.s.write(b'@')
        log.info('Stopping.')
        time.sleep(MP_789A_4.WR_DLY)

        self._moving = False
        self._homing = False

    def is_moving(self):
        """_summary_

        Returns:
            _type_: Is moving (True) or is not moving (False).
        """

        log.debug('func: is_moving')

        if self._backlash_lock:
            log.info('is_moving is returning true because the Backlash lock is active.')
            return True
        elif self._homing:
            return True
        else:
            return self._moving

        # # If the `_backlash_lock` flag is set then the 789A-4 is already performing a move command.
        # # If the `_backlash_lock` flag is set then the 789A-4 is already performing a move command.
        # # if self._backlash_lock:
        # #     log.warn('BACKLASH LOCK is set. Device is moving.')
        # #     return True

        # # Acquire the mutex and begin inquiring as to the moving status (double-redundant).
        # self.moving_poll_mutex.acquire()
        # log.debug('ACQUIRED MOVING POLL MUTEX')
        # status = self.s.xfer([b'^']).decode('utf-8').rstrip()
        # # self.s.write(b'^')
        # # time.sleep(MP_789A_4.WR_DLY)
        # # status = self.s.read(128).decode('utf-8').rstrip()
        # time.sleep(MP_789A_4.WR_DLY)
        # status2 = self.s.xfer([b'^']).decode('utf-8').rstrip()
        # # self.s.write(b'^')
        # # time.sleep(MP_789A_4.WR_DLY)
        # # status2 = self.s.read(128).decode('utf-8').rstrip()
        # time.sleep(MP_789A_4.WR_DLY)
        # self.moving_poll_mutex.release()

        # # Check the returned status to determine movement status.
        # if ('0' in status and '0' in status2) and ('+' not in status and '+' not in status2 and '-' not in status and '-' not in status2):
        #     log.info('MOVING STATUS >>>%s<<< >>>%s<<<; INDICATES STOPPED.'%(status, status2))
        #     self._moving = False
        #     return False
        # else:
        #     log.info('MOVING STATUS: >>>%s<<<; INDICATES MOVING.'%(status))
        #     self._moving = True
        #     return True

    # Internal-calling only.
    def _is_moving(self):
        self.moving_poll_mutex.acquire()

        log.debug('ACQUIRED MOVING POLL MUTEX')
        status = self.s.xfer([b'^']).decode('utf-8').rstrip()
        log.debug('789 _status:', status)
        time.sleep(MP_789A_4.WR_DLY)

        if ('0' in status) and ('+' not in status and '-' not in status):
            # self._moving = False
            moving = False
        else:
            # self._moving = True
            moving = True

        self.moving_poll_mutex.release()

        self._moving = moving
        return moving

    def is_homing(self):
        """ Return homing status.

        Returns:
            _type_: Homing (True) or not homing (False).
        """

        log.debug('func: is_homing')
        return self._homing

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, backlash: int):
        """ Moves to a position based on the software's understanding of where the 789A-4 last was.
            Position information is not tracked by the 789A-4.

        Args:
            position (int): The position in steps.
            backlash (int): The amount of backlash correction to perform in steps.
        """

        if self._homing or self._moving or self._backlash_lock:
            log.warn(f'Device is homing ({self._homing}), moving ({self._moving}), or performing backlash correction ({self._backlash_lock}). Cannot move.')
            return
        
        # self.moving_poll_mutex.acquire()
        self._moving = True

        try:

            self.stop_queued = 0

            log.debug('func: move_to')
            
            steps = position - self._position

            if (steps < 0) and (backlash > 0):
                self._backlash_lock = True

                try:
                    if self.stop_queued == 0:
                        log.debug('MOVE-DEBUG: Performing overshot manuever.')
                        self.move_relative(steps - backlash, backlash_bypass=True)

                    if self.stop_queued == 0:
                        log.debug('MOVE-DEBUG: Performing backlash correction.')
                        self.move_relative(backlash, backlash_bypass=True)

                except Exception as e:
                    log.error('Error during backlash correction:', e)
                    self._backlash_lock = False
                    raise e
                
                self._backlash_lock = False
            else:
                log.debug('MOVE-DEBUG: Performing simple no-backlash move.')
                self.move_relative(steps)

            self.stop_queued = 0
            self._backlash_lock = False

        except Exception as e:
            # self.moving_poll_mutex.release()
            raise e

        # # Backlash correction only necessary if (1) requested and (2) moving in the negative direction.
        # log.warn('BACKLASH: %d'%(backlash))
        # log.warn('BACKLASH: %d'%(backlash))
        # log.warn('BACKLASH: %d'%(backlash))
        # if (steps < 0) and (backlash > 0):
        #     # Acquire `_backlash_lock` (should probably be a mutex lock, not a flag). Prevents movement before backlash.
        #     self._backlash_lock = True
            
        #     # Check if we have a queued stop command prior to moving.
        #     if self.stop_queued == 0:
        #         self.move_relative(steps - backlash)
            
        #     # Check if we have a queued stop command prior to performing backlash correction.
        #     if self.stop_queued == 0:
        #         self.move_relative(backlash)
            
        #     # Release lock.
        #     self._backlash_lock = False
        # else:
        #     # Simple move.
        #     self.move_relative(steps)

        # # Clear all queued stops since move/stop has been processed.
        # self.stop_queued = 0

    def move_relative(self, steps: int, backlash_bypass=False):
        """ Private function for use by `move_to()`. Moves a relative number of steps.

        Args:
            steps (int): Number of steps to move.
        """

        log.debug('func: move_relative')
        log.info('Being told to move %d steps.'%(steps))

        # Query limit switch status.
        # self.s.write(b']')
        # time.sleep(MP_789A_4.WR_DLY)     
        # rx = self.s.read(128).decode('utf-8')
        rx = self.s.xfer([b']']).decode('utf-8')

        if steps > 0:
            # Verify we are not at the upper limit.
            if '64' in rx:
                log.warn('Upper limit switch hit. Cannot move further in this direction.')
                raise RuntimeError('Upper limit switch hit. Cannot move further in this direction.')

            log.info('Moving...')
            self._moving = True
            log.debug([b'+%d'%(steps)])
            # self.s.write(b'+%d'%(steps))

            self.s.xfer([b'+%d'%(steps)])
            time.sleep(MP_789A_4.WR_DLY)
        elif steps < 0:
            # Verify we are not at the lower limit.
            if '128' in rx:
                log.warn('Lower limit switch hit. Cannot move further in this direction.')
                raise RuntimeError('Lower limit switch hit. Cannot move further in this direction.')

            log.info('Moving...')
            self._moving = True
            log.debug(b'-%d'%(steps))
            # self.s.write(b'-%d'%(steps * -1))

            self.s.xfer([b'-%d'%(steps)])
            time.sleep(MP_789A_4.WR_DLY)
        else:
            log.info('Not moving (0 steps).')
            return
        self._position += steps

        self._moving = True
        if not backlash_bypass:
            while self.is_moving():
                log.debug('(not bypass) BLOCKING until movement is completed.')
                time.sleep(0.05)
        elif backlash_bypass:
            while self._moving:
                log.debug('(bypass) BLOCKING until movement is completed.')
                time.sleep(0.05)

        log.debug('FINISHED BLOCKING because moving is', self._moving)
        time.sleep(MP_789A_4.WR_DLY)
        
    def short_name(self):
        """ Returns the short name of the device.

        Returns:
            str: The short name.
        """

        log.debug('func: short_name')
        return self.s_name

    def long_name(self):
        """ Returns the full name of the device.

        Returns:
            str: The full name.
        """

        log.debug('func: long_name')
        return self.l_name
    
    def open(self):
        pass

    def close(self):
        self.s.close()


class MP_789A_4_DUMMY(StageDevice):
    def backend(self)->str:
        return 'MP_789A_4'
    
    def __init__(self, port):
        self.s_name = 'MP789_DUMMY'
        self.l_name = 'McPherson 789A-4 (DUMMY)'

        log.info('Attempting to connect to McPherson Model 789A-4 Scan Controller on port %s.'%(port))

        if port is not None:     
            log.info('McPherson model 789A-4 (DUMMY) Scan Controller generated.')
        
        self._position = 0
        self._moving = False
        self._homing = False
        self.home()
        time.sleep(MP_789A_4.WR_DLY * 5)

    def home(self)->bool:
        self._homing = True
        log.debug('func: home')
        log.info('Beginning home.')
        log.info('Finished homing.')
        success = True

        if success:
            self._position = 0

        self._homing = False
        return success

    def get_position(self):
        log.debug('func: get_position')
        return self._position
    
    # Triple-redundant serial stop command.
    def stop(self):
        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(MP_789A_4.WR_DLY)

        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(MP_789A_4.WR_DLY)

        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(MP_789A_4.WR_DLY)

    def is_moving(self):
        log.debug('func: is_moving')
        return self._moving
    
    def is_homing(self):
        log.debug('func: is_homing')
        return self._homing

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, backlash: int):
        log.debug('func: move_to')
        steps = position - self._position

        # Stops the moving updater from starting more than once. <-- Huh?

        if (steps < 0) and (backlash > 0):
            self.move_relative(steps - backlash)
            self.move_relative(backlash)
        else:
            self.move_relative(steps)

    def move_relative(self, steps: int):
        log.debug('func: move_relative')
        log.debug(b'+%d\r', steps)
        self._position += steps

        i=0
        # moving = True
        while i<15:
            log.debug('BLOCKING')
            time.sleep(MP_789A_4.WR_DLY)
            if not self.is_moving():
                log.info('Found to be NOT MOVING.',i)
                i+=1
            else:
                log.info('Found to be MOVING',i)
                i=0
        log.debug('FINISHED BLOCKING because moving is', i)
        time.sleep(MP_789A_4.WR_DLY)


    def short_name(self):
        log.debug('func: short_name')
        return self.s_name

    def long_name(self):
        log.debug('func: long_name')
        return self.l_name

""" 
McPherson Model 789A-4 Scan Controller Command Set

ASCII       Value   Desc.
-----------------------------------------------
[SPACE]     0x20    Init   
[CR]        0x0D    Carriage Return
@                   Soft Stop
A0                  Set Home Switch OFF
A8                  Set Home Switch ON
A24                 Enable Homing Circuit
^C          0x03    Reset
C1                  Clear
F1000,0             Find Home
G                   Run Internal Program
I                   Starting Velocity
K                   Ramp Slope
P                   Enter & Exit Program Mode
S                   Save
V                   Scanning Velocity
X                   Examine Parameters
]                   Read Limit Switch Status
+                   Index Scan In Up Direction
-                   Index Scan In Down Direction
^                   Read Moving Status
"""
