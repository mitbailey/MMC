#
# @file mp_792.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Driver for the McPherson Series 792 multi-axis Motor Controller.
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

import threading
from threading import Lock
import serial
import time
from utilities import ports_finder
from utilities import safe_serial
from utilities import log

from drivers.mp_789a_4 import MP_789A_4
from drivers.mp_789a_4 import MP_789A_4_DUMMY

class MP_792:
    AXES = [b'A0', b'A8', b'A16', b'A24']
    WR_DLY = 0.05

    MAX_VEL = 60000
    DEF_VEL = 60000
    MIN_VEL = 0

    def __init__(self, port: serial.Serial, axes: int = 4):
        """ MP_792 constructor.

        Args:
            port (serial.Serial): The port on which to attempt a connection.
            axes (int, optional): The number of active axes on the 792. Defaults to 4.

        Raises:
            RuntimeError: _description_
            RuntimeError: _description_
            RuntimeError: _description_
            RuntimeError: _description_
        """

        self._home_speed_mult_l = [1] * axes
        self._move_speed_mult_l = [1] * axes
        self.num_axes = axes
        self.s_name = 'MP792'
        self.l_name = 'McPherson 792'
        self.axis_alive = [False] * axes
        self._is_homing = [False] * axes
        self._is_moving_l = [False] * axes
        self.current_axis = 0
        self._backlash_lock_l = [False] * axes
        self.stop_queued_l = [0] * axes

        if port is None:
            log.error('Port is none type.')
            raise RuntimeError('Port is none type.')

        log.info('Attempting to connect to McPherson 792 on port %s.'%(port))

        self._position = [0] * 4

        ser_ports = ports_finder.find_serial_ports()
        if port not in ser_ports:
            log.error('Port not valid. Is another program using the port?')
            log.error('%s\nnot found in\n%s'%(port, ser_ports))
            raise RuntimeError('Port not valid. Is another program using the port?')

        self.s = safe_serial.SafeSerial(port, 9600, timeout=0.5)
        rx = self.s.xfer([b' '], custom_delay=MP_792.WR_DLY)
        # self.s.write(b' \r')
        # time.sleep(MP_792.WR_DLY)
        # rx = self.s.read(128)#.decode('utf-8').rstrip()   
        log.debug(rx)

        if rx is None or rx == b'':
            raise RuntimeError('Response timed out.')
        elif rx == b' v2.55\r\n#\r\n':
            log.info('McPherson model 792 Scan Controller found.')
        elif rx == b' #\r\n':
            log.info('McPherson model 792 Multi-Axis already initialized.')
        else:
            raise RuntimeError('Invalid response.')

        # TODO: (This is new) Spawn the t_movement_status thread. This thread will update the current movement status in line with what the device can handle. This is a break-away from the previous paradigm where only when asked would we check. This didnt make much sense.
        # Starting movement watchdog.
        self.movement_status_tid = threading.Thread(target=self.movement_status_thread)
        self.movement_status_tid.start()

        log.info('Checking axes...')
        for i in [2, 0, 3, 1]:
            log.debug('WR:', MP_792.AXES[i] + b'\r')
            alivestat = self.s.xfer([MP_792.AXES[i], b']'], custom_delay=MP_792.WR_DLY)
            alivestat = alivestat.decode('utf-8')
            # self.s.write(MP_792.AXES[i] + b'\r')
            # time.sleep(MP_792.WR_DLY)
            # log.debug('RD:', self.s.read(128))
            # time.sleep(MP_792.WR_DLY)

            # log.debug('WR:', b']\r')
            # self.s.write(b']\r')
            # time.sleep(MP_792.WR_DLY)
            # alivestat = self.s.read(128).decode('utf-8')
            log.debug('RD:', alivestat)
            time.sleep(MP_792.WR_DLY)

            if '192' in alivestat:
                log.info('Axis %d is dead.'%(i))
                self.axis_alive[i] = False
            else:
                log.info('Axis %d is alive.'%(i))
                self.axis_alive[i] = True
                
                self.home(i)

        log.info('McPherson 792 initialization complete.')

    def movement_status_thread(self):
        # This thread runs in the background.
        # It will be the only thing which calls the internal _is_moving() function.
        # The middleware calls the external is_moving() function.
        # This way we can ensure that the device is only queried for movement status when it is safe to do so.


        any_alive = False

        while True:
            time.sleep(0.25)

            alive_axes_indices = [i for i, v in enumerate(self.axis_alive) if v]

            moving_axes = 0

            for i in alive_axes_indices:
                any_alive = True
                if self._is_moving_l[i]:
                    moving_axes += 1

            if not any_alive:
                log.error('No axes are alive.')
                continue

            if moving_axes > 1:
                log.error('Multiple axes are moving.')
                log.error('Cancelling all movement.')

                for i in alive_axes_indices:
                    self.stop(i)

                continue

            elif moving_axes == 1:
                moving_axis_index = next((i for i, v in enumerate(self._is_moving_l) if v), None)

                # Check if the backlash lock is active. If so, we should check again later.
                if self._backlash_lock_l[moving_axis_index]:
                    # log.info('Backlash lock is active. Skipping movement inquiry.')
                    log.info('Backlash lock is active, but not skipping movement inquiry.')

                    # continue

                # Update the movement status of the axis which is moving.
                log.info(f'Checking movement status of axis {moving_axis_index}.')
                self._is_moving_l[moving_axis_index] = self._is_moving(moving_axis_index)
                log.info(f'Axis {moving_axis_index} is moving? {self._is_moving_l[moving_axis_index]}.')

            # Checking for movement in this last case isn't necessary because we know when we initiate an axis move - it should be set to True (moving) when its told to move. The assumption should be that it does begin to move. Then, we use the previous case to prove it isn't moving once its stopped (or failed to start moving).
            elif moving_axes == 0:
                # Update the movement status of all alive axes, since none are reported as moving.
                log.info('No axes have been marked or reported as moving. Skipping movement inquiry.')

    # Axis needs to be set by passing MP_792.AXES[axis] + b'\r' command every time we do anything.
    def set_axis_cmd(self, axis: int):
        return MP_792.AXES[axis] + b'\r'

    def home(self, axis: int)->bool:
        # Deny the home is any axis is busy.
        if any(self._is_homing) or any(self._is_moving_l) or any(self._backlash_lock_l):
            log.warn(f'Device is busy: an axis is already homing ({self._is_homing}) or moving ({self._is_moving_l}) or locked for backlash ({self._backlash_lock_l}).')
            return False

        HOME_TIME = 5*60 # 5 minutes - homing will timeout after 5 minutes

        log.info('Beginning home for 792 axis %d.'%(axis))
        self._is_homing[axis] = True
        self._is_moving_l[axis] = True # we set the movement, movement_status_thread will unset

        # Set the movement speed for homing.
        self._enact_speed_factor(self._home_speed_mult_l[axis], axis)

        if axis == 2:
            spd = 5000
            log.debug(f'Speed would have been {spd} but is being multiplied by {self._home_speed_mult_l[axis]}.')
            spd = spd * self._home_speed_mult_l[axis]
            spd = int(spd)
            # home_cmd = b'M-5000'
            home_cmd = b'M-' + bytes(str(spd), 'utf-8')
            log.debug(f'Speed is now {spd} and the command is {home_cmd}.')
        else:
            spd = 10000
            log.debug(f'Speed would have been {spd} but is being multiplied by {self._home_speed_mult_l[axis]}.')
            spd = spd * self._home_speed_mult_l[axis]
            spd = int(spd)
            # home_cmd = b'M-10000'
            home_cmd = b'M-' + bytes(str(spd), 'utf-8')
            log.debug(f'Speed is now {spd} and the command is {home_cmd}.')

        self.s.xfer([self.set_axis_cmd(axis), home_cmd], custom_delay=MP_792.WR_DLY)

        start_time = time.time()
        success = True
        while True:
            current_time = time.time()

            log.info('Time spent homing:', current_time - start_time)

            # moving = self._is_moving(axis)
            time.sleep(0.5)
            moving = any(self._is_moving_l)

            limstat = self.s.xfer([self.set_axis_cmd(axis), b']'], custom_delay=MP_792.WR_DLY)
            limstat = limstat.decode('utf-8')

            log.debug('limstat:', limstat)

            if moving:
                log.info('Moving...')
            if '0' not in limstat:
                log.info('Not yet homed...')
            
            if not moving and '128' in limstat:
                log.info('Moving has completed - homing successful.')
                break
            elif (not moving and '128' not in limstat) or (current_time - start_time > HOME_TIME):
                log.warn('Moving has completed - homing failed.')

                log.error('Homing failed.')
                self.s.xfer([self.set_axis_cmd(axis), b'@'], custom_delay=MP_792.WR_DLY)
                
                self._is_homing[axis] = False
                # Reset the movement speed.
                self._enact_speed_factor(self._move_speed_mult[axis], axis)
                return False

            time.sleep(MP_792.WR_DLY * 5)

        if (self._is_moving(axis)):
            log.warn('Post-home movement detected. Entering movement remediation.')
            self.s.xfer([self.set_axis_cmd(axis), b'@'], custom_delay=MP_792.WR_DLY)

            time.sleep(MP_792.WR_DLY * 10)
        stop_waits = 0
        while(self._is_moving(axis)):
            if stop_waits > 3:
                stop_waits = 0
                log.warn('Re-commanding that device ceases movement.')
                self.s.xfer([self.set_axis_cmd(axis), b'@'], custom_delay=MP_792.WR_DLY)
                    
            stop_waits += 1
            log.warn('Waiting for device to cease movement.')
            time.sleep(MP_792.WR_DLY * 10)

        self._position[axis] = 0
        self._is_homing[axis] = False

        # Reset the movement speed.
        self._enact_speed_factor(self._move_speed_mult[axis], axis)

        return True

    def get_position(self, axis: int):
        return self._position[axis]

    # Triple-redundant serial stop command.
    # TODO: Needs to stop all axes simultaneously since the 'switch' inside will mess up whats doing what.
    def stop(self, axis: int):
        self.stop_queued_l[axis] = 1

        self.s.xfer([self.set_axis_cmd(axis), b'@'], custom_delay=MP_792.WR_DLY)

        log.info('Stopping.')
        time.sleep(MP_792.WR_DLY)

        self.s.xfer([self.set_axis_cmd(axis), b'@'], custom_delay=MP_792.WR_DLY)

        log.info('Stopping.')
        time.sleep(MP_792.WR_DLY)

        self.s.xfer([self.set_axis_cmd(axis), b'@'], custom_delay=MP_792.WR_DLY)

        log.info('Stopping.')
        time.sleep(MP_792.WR_DLY)

        self._is_moving_l[axis] = False
        self._is_homing[axis] = False

    # Publicly callable is_moving() function.
    def is_moving(self, axis: int):
        if self._backlash_lock_l[axis]:
            log.info('is_moving is returning true because the Backlash lock is active.')
            return True
        elif self._is_homing[axis]:
            return True
        else:
            return self._is_moving_l[axis]

    # Internal-calling only.
    def _is_moving(self, axis: int):

        sum_moving = sum(self._is_moving_l)
        sum_homing = sum(self._is_homing)

        if sum_moving > 1:
            log.fatal(f'Multiple axes are moving: {self._is_moving_l}.')
            exit(-1)
            raise RuntimeError('Multiple axes are moving.')
        
        if sum_homing > 1:
            log.fatal(f'Multiple axes are homing: {self._is_homing}.')
            exit(-1)
            raise RuntimeError('Multiple axes are homing.')

        # We want to deny access to the device if 
        # - a different axis is moving.
        # - this axis is mid-backlash.
        # It doesn't matter if this axis is listed as moving or not.
        # This will prevent switching to another axis mid-move.

        _is_moving_others = [v for i, v in enumerate(self._is_moving_l) if not i == axis]
        _is_homing_others = [v for i, v in enumerate(self._is_homing) if not i == axis]
        _backlash_lock_others = [v for i, v in enumerate(self._backlash_lock_l) if not i == axis]
        # This function, the INTERNAL movement query, needs to return truly whether its moving or not. I dont care about backlash locks. We can check for that ourselves. The EXTERNAL movement function is more of an "is busy", and should return true if backlashing.

        if any(_is_moving_others) or any(_is_homing_others) or any(_backlash_lock_others):
            log.info(f'Device is busy: another axis besides #{axis} is already homing ({self._is_homing}) or moving ({self._is_moving_l}) or locked for backlash ({self._backlash_lock_l}).')
            log.info(f'Returning the previous movement status of this axis (axis {axis}).')
            return self._is_moving_l[axis]
        
        # # Check that the axis we are trying to operate on is the axis that is already busy. If so let it through.
        # if (any(self._is_homing) or any(self._is_moving_l) or any(self._backlash_lock_l)) and not (self._is_homing[axis] or self._is_moving_l[axis] or self._backlash_lock_l[axis]):
        #     log.info(f'Device is busy: another axis is already homing ({self._is_homing}) or moving ({self._is_moving_l}) or locked for backlash ({self._backlash_lock_l}).')
        #     return True
        
        status = self.s.xfer([self.set_axis_cmd(axis), b'^'], custom_delay=MP_792.WR_DLY)
        status = status.decode('utf-8').rstrip()

        log.debug('792 _status:', status)
        time.sleep(MP_792.WR_DLY)

        if ('0' in status) and ('+' not in status and '-' not in status):
            self._is_moving_l[axis] = False
            log.debug("Returning from _is_moving")
            log.info('792 Axis %d IS NOT moving because status1: %s'%(axis, status))
            return False
        else:
            self._is_moving_l[axis] = True
            log.debug("Returning from _is_moving")
            log.info('792 Axis %d IS YES moving because status1: %s'%(axis, status))
            return True
        
    def is_homing(self, axis: int):
        return self._is_homing[axis]

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, axis: int, backlash: int):
        # If anything is moving or homing, prevent a move.
        if any(self._is_homing) or any(self._is_moving_l) or any(self._backlash_lock_l):
            log.warn(f'Device is busy: an axis is already homing ({self._is_homing}) or moving ({self._is_moving_l}) or locked for backlash ({self._backlash_lock_l}).')
            return
        
        # Reset the stop queued such that we dont immediately stop from an old stop request.
        # Otherwise, this enables us to cancel backlash, etc, when stops are desired.
        self.stop_queued_l[axis] = 0

        log.debug('MOVE-DEBUG: Performing a move with backlash value: ', backlash)

        steps = position - self._position[axis]

        if (steps < 0) and (backlash > 0):
            self._backlash_lock_l[axis] = True

            try:
                if self.stop_queued_l[axis] == 0:
                    log.debug('MOVE-DEBUG: Performing overshoot manuever.')
                    self.move_relative(steps - backlash, axis, backlash_bypass=True)
                
                if self.stop_queued_l[axis] == 0:
                    log.debug('MOVE-DEBUG: Performing backlash correction.')
                    self.move_relative(backlash, axis, backlash_bypass=True)
                    
                log.debug('MOVE-DEBUG: Move complete.')
            except Exception as e:
                self._backlash_lock_l[axis] = False
                raise e

            self._backlash_lock_l[axis] = False
        else:
            log.debug('MOVE-DEBUG: Performing backlash-free move.')
            self.move_relative(steps, axis)

        # Reset the stop queue.
        self.stop_queued_l[axis] = 0

    def move_relative(self, steps: int, axis: int, backlash_bypass: bool = False):
        if any(self._is_homing) or any(self._is_moving_l) or (any(self._backlash_lock_l) and not backlash_bypass):
            log.warn(f'Device is busy: another axis is already homing ({self._is_homing}) or moving ({self._is_moving_l}) or locked for backlash ({self._backlash_lock_l}).')
            return False

        self._is_moving_l[axis] = True

        log.info('Being told to move %d steps.'%(steps))

        if steps > 0:
            log.info('Moving...')
            log.debug(b'+%d\r'%(steps))
            self.s.xfer([self.set_axis_cmd(axis), b'+%d'%(steps)], custom_delay=MP_792.WR_DLY)
            
            time.sleep(MP_792.WR_DLY)
        elif steps < 0:
            log.info('Moving...')
            log.debug(b'-%d\r'%(steps * -1))
            self.s.xfer([self.set_axis_cmd(axis), b'-%d'%(steps * -1)], custom_delay=MP_792.WR_DLY)
            
            time.sleep(MP_792.WR_DLY)
        else:
            log.info('Not moving (0 steps).')
        self._position[axis] += steps

        # Blocks until the move is complete (this may not even be necessary..?).
        while True:
            log.debug('BLOCKING until movement is completed.')
            time.sleep(0.5)
            if not self._is_moving_l[axis]:
                log.info('Found to be NOT MOVING.')
                break
        log.debug('FINISHED BLOCKING because moving is', self._is_moving_l)
        time.sleep(MP_792.WR_DLY)

    def set_home_speed_mult(self, speed, axis: int):
        log.debug(f'Setting home speed multiplier for axis {axis} to {speed}.')
        self._home_speed_mult_l[axis] = speed

    def set_move_speed_mult(self, speed, axis: int):
        log.info(f'Setting move speed multiplier for axis {axis} to {speed}.')
        self._move_speed_mult_l[axis] = speed

        self._enact_speed_factor(self._move_speed_mult_l[axis], axis)

    def _enact_speed_factor(self, speed_factor, axis: int):
        vel_int = int(speed_factor * MP_792.MAX_VEL)

        log.debug('_enact_speed_factor: (pre)', vel_int)

        if vel_int > MP_792.MAX_VEL:
            vel_int = MP_792.MAX_VEL
        elif vel_int < MP_792.MIN_VEL:
            vel_int = MP_792.MIN_VEL

        msg = f'V{str(vel_int)}'
        rx = self.s.xfer([self.set_axis_cmd(axis), msg.encode('utf-8')], custom_delay=MP_792.WR_DLY).decode('utf-8')

        log.debug('_enact_speed_factor: (post)', vel_int)

    def _reset_speed_factor(self, speed_factor, axis: int):
        msg = f'V{str(MP_792.DEF_VEL)}'
        rx = self.s.xfer([self.set_axis_cmd(axis), msg.encode('utf-8')], custom_delay=MP_792.WR_DLY).decode('utf-8')

    def short_name(self):
        return self.s_name

    def long_name(self):
        return self.l_name

class MP_792_DUMMY:
    AXES = [b'A0', b'A8', b'A16', b'A24']

    def __init__(self, port: serial.Serial, axes: int = 4):
        self.num_axes = axes
        self.s_name = 'MP792'
        self.l_name = 'McPherson 792'
        self.axis_alive = [False] * axes
        self._is_homing = [False] * axes
        self._is_moving_l = [False] * axes
        self.current_axis = 0
        self._home_speed_mult_l = [1] * axes
        self._move_speed_mult_l = [1] * axes

        if port is None:
            log.error('Port is none type.')
            raise RuntimeError('Port is none type.')

        log.info('Attempting to connect to McPherson 792 on port %s.'%(port))

        self._position = [0] * 4

        log.info('Checking axes...')
        for i in range(4):
            log.debug('WR:', MP_792.AXES[i] + b'\r')
            time.sleep(MP_792.WR_DLY)

            log.debug('WR:', b']\r')
            
            time.sleep(MP_792.WR_DLY * 15)
            
            log.debug('RD:', 'Dummy - Axes Always Alive')
            time.sleep(MP_792.WR_DLY)


            log.debug('Axis %d is alive.'%(i))
            self.axis_alive[i] = True

            self.home(i)

        time.sleep(MP_792.WR_DLY * 50)

        log.info('McPherson 792 initialization complete.')

    def set_axis(self, axis: int):
        if axis != self.current_axis:
            log.debug('WR:', MP_792.AXES[axis] + b'\r')
            self.current_axis = axis
            time.sleep(MP_792.WR_DLY)

    def home(self, axis: int)->bool:
        # self.set_axis(axis)

        log.info('Beginning home for 792 axis %d.'%(axis))
        self._is_homing[axis] = True

        log.debug('WR:', b'M-10000\r')
        time.sleep(MP_792.WR_DLY * 5)

        start_time = time.time()
        retries = 3
        success = True
        
        # The standard is for the device drivers to read 0 when homed if the controller does not itself provide a value.
        # It is up to the middleware to handle zero- and home-offsets.
        self._position[axis] = 0
        self._is_homing[axis] = False
        return True

    def get_position(self, axis: int):
        return self._position[axis]
    
    # Triple-redundant serial stop command.
    def stop(self):
        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(MP_792_DUMMY.WR_DLY)

        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(MP_792_DUMMY.WR_DLY)

        # self.s.write(b'@\r')
        log.info('Stopping.')
        time.sleep(MP_792_DUMMY.WR_DLY)

        

    def _is_moving(self, axis: int):
        # self.set_axis(axis)

        self._is_moving_l[axis] = False
        return False

    def is_moving(self, axis: int):
        return self._is_moving_l[axis]

    def is_homing(self, axis: int):
        return self._is_homing[axis]

    # Moves to a position, in steps, based on the software's understanding of where it last was.
    def move_to(self, position: int, axis: int, backlash: int):
        # self.set_axis(axis)

        steps = position - self._position[axis]

        if (steps < 0) and (backlash > 0):
            self.move_relative(steps - backlash, axis)
            self.move_relative(backlash, axis)
        else:
            self.move_relative(steps, axis)

    def move_relative(self, steps: int, axis: int):
        # self.set_axis(axis)

        self._position[axis] += steps

        while self._is_moving(axis):
            log.debug('BLOCKING')
            time.sleep(MP_792.WR_DLY * 5)
        log.debug('FINISHED BLOCKING')

    def set_home_speed_mult(self, speed, axis: int):
        log.info(f'Setting home speed multiplier for axis {axis} to {speed}.')
        self._home_speed_mult_l[axis] = speed

    def set_move_speed_mult(self, speed, axis: int):
        log.info(f'Setting move speed multiplier for axis {axis} to {speed}.')
        self._move_speed_mult_l[axis] = speed

    def short_name(self):
        return self.s_name

    def long_name(self):
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
