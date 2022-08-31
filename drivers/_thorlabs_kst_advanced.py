# %% Imports
from __future__ import annotations
from asyncore import poll
import sys
import weakref
from nicelib import load_lib, NiceLib, Sig, NiceObject, RetHandler, ret_ignore
from cffi import FFI
from inspect import getmembers
import warnings
from time import sleep
import math as m
import threading

from ._thorlabs_kst_wrap_basic import *

def __funcname__():
    import inspect
    return inspect.stack()[1][3]

#%%
################################################################################ 
############### Level 3 Wrapper (final stage) begin ############################

# %%
class Thorlabs: # Wrapper class for TLI methods
    TYPE_KST101 = 26
    @staticmethod
    def ListDevicesAny(ser_buf_len: int = 512) -> list:
        """List all available (unopened) Thorlabs devices.

        Args:
            ser_buf_len (int, optional): String buffer length where the serials are read into. Defaults to 512.

        Raises:
            RuntimeError: Failed to build device list
            RuntimeError: Failed to get device list
            RuntimeWarning: Incomplete serial found

        Returns:
            list: Serial numbers of available devices
        """
        ret = TLIBase.BuildDeviceList()
        if ret:
            raise RuntimeError('Could not create device list: (%d) %s'%(ret, err_codes[ret]))
        num_devices = TLIBase.GetDeviceListSize()
        if not num_devices:
            return []
        ffi = FFI()
        ser_buf = ffi.new('char[]', ser_buf_len)
        ret = TLIBase.GetDeviceListExt(ser_buf, ser_buf_len)
        if ret:
            raise RuntimeError('Thorlabs:%s(): %s (%d).'%(__funcname__(), err_codes[ret], ret))
        ser_buf = ffi.string(ser_buf).decode('utf-8')
        ser_vals = ser_buf.split(',')
        for idx in range(len(ser_vals)):
            if ser_vals[idx] == '':
                del ser_vals[idx]
            elif len(ser_vals[idx]) != 8:
                del ser_vals[idx]
                warnings.warn('Serial %s invalid, please check, consider increasing buffer length.')
            else:
                ser_vals[idx] = int(ser_vals[idx])
        ser_vals.sort() # sort by ID
        return ser_vals

    @staticmethod
    def ListDevices(typeID: int) -> list:
        """List all available (unopened) Thorlabs devices of given type ID.

        Args:
            typeID (int): Thorlabs Device Type ID Number

        Raises:
            RuntimeError: Failed to build device list
            RuntimeError: Failed to get device list

        Returns:
            list: Serial numbers of available devices
        """
        ret = TLIBase.BuildDeviceList()
        if ret:
            raise RuntimeError('Could not create device list: (%d) %s'%(ret, err_codes[ret]))
        num_devices = TLIBase.GetDeviceListSize()
        if not num_devices:
            return []
        ffi = FFI()
        ser_buf_len = 100
        ser_buf = ffi.new('char[]', ser_buf_len)
        ret = TLIBase.GetDeviceListByTypeExt(ser_buf, ser_buf_len, typeID)
        if ret:
            raise RuntimeError('Could not get device list by type ID %d: (%d) %s'%(typeID, ret, err_codes[ret]))
        ser_buf = ffi.string(ser_buf).decode('utf-8')
        ser_vals = ser_buf.split(',')
        for idx in range(len(ser_vals)):
            if ser_vals[idx] == '':
                del ser_vals[idx]
            else:
                ser_vals[idx] = int(ser_vals[idx])
        ser_vals.sort()
        return ser_vals

    @staticmethod
    def GetDeviceInfo(serialNumber: int | list) -> dict:
        """Get Device Info for a given Thorlabs Serial Number.

            Args:
                typeID (int | list(int)): Thorlabs Serial Numbers.

            Raises:
                RuntimeError: Could not get device info for serial.

            Returns:
                dict: Device Information (struct TLI_DeviceInfo)
        """

        if isinstance(serialNumber, int):
            ffi = FFI()
            ffi.cdef("""
            struct TLI_DeviceInfo
            {
                DWORD typeID;
                char description[65];
                char serialNo[16];
                DWORD PID;
                bool isKnownType;
                int motorType;
                bool isPiezoDevice;
                bool isLaser;
                bool isCustomType;
                bool isRack;
                short maxChannels;
            };
            """, packed=True) # define struct, with packing
            ser_buf = ffi.new('struct TLI_DeviceInfo *') # create memory for struct
            ret = TLIBase.GetDeviceInfo(str(serialNumber), ser_buf) # pass pointer
            if not ret:
                raise RuntimeError('Could not get device info for serial %d'%(serialNumber))
            return cdata_dict(ser_buf, ffi)

        elif isinstance(serialNumber, list):
            out = []
            for s in serialNumber:
                out.append(Thorlabs.GetDeviceInfo(s))
            return out

        else:
            raise TypeError('Serial number can be an int or a list of int.')

    class KST101: # Subclass for KST101 devices
        # API calls; possible examples.
        """
            get_status_n
            get_status
            wait_for_status

            home
            is_homing
            is_homed
            wait_for_home

            get_position
            set_position_reference
            move_by
            move_to
            jog
            is_moving
            wait_move
            stop
            wait_for_stop

            get_velocity_parameters
            setup_velocity
            get_jog_parameters
            setup_jog
            get_homing_parameters
            setup_homing
            get_gen_move_parameters
            setup_gen_move
            get_limit_switch_parameters
            setup_limit_switch
            get_kcube_trigio_parameters
            setup_kcube_trigio
            get_kcube_trigpos_parameters
            setup_kcube_trigpos
        """
        # TLI List method
        open_devices = [] # List of opened devices

        avail_stages = {}
        avail_stages['ZST25'] = 2184560.64
        @staticmethod
        def _ListDevices() -> list:
            """List all available KST101 devices (including opened devices).

            Returns:
                list: Serial numbers of available KST101 devices.

            NOTE: Backport listing opened devices feature to Thorlabs.ListDevicesAny() and Thorlabs.ListDevices()
            """
            devs = Thorlabs.ListDevices(Thorlabs.TYPE_KST101) # special case
            _devs = Thorlabs.KST101.open_devices + devs
            _devs = list(set(_devs))
            return _devs
        
        # Init stores the serial number
        def __init__(self, serialNumber: int, pollingIntervalMs: int = 100): # should also get the stage here
            """Create an instance of Thorlabs KST101 Stepper Motor Controller

            Args:
                serialNumber (int): Serial number of the KST101 Controller

            Raises:
                ValueError: Invalid serial number
                RuntimeError: Instance of KST101 exists with this serial number
                RuntimeError: Serial number not in device list
            """
            self.poll_thread = None
            if str(serialNumber)[:2] != str(Thorlabs.TYPE_KST101):
                raise ValueError('Invalid serial %d: KST101 Serial starts with %s'%(serialNumber, str(Thorlabs.TYPE_KST101)))
            elif serialNumber in Thorlabs.KST101.open_devices:
                raise RuntimeError('Serial %d already in use.'%(serialNumber))
            elif serialNumber not in Thorlabs.KST101._ListDevices():
                raise RuntimeError('Serial %d not in device list.'%(serialNumber))
            self.serial = str(serialNumber)
            self.open = False
            self._Open(pollingIntervalMs)
            self.moving = False
            self.homed = False
            self.homing = False
            self._mm_to_idx = 0 # this will cause errors unless a stage is set
            self.keep_polling = True
            self.poll_interval = pollingIntervalMs * 0.001
            self.mutex = threading.Lock()
            self.cond = threading.Condition(self.mutex)
            self.poll_thread = threading.Thread(target = Thorlabs.KST101.poll_status, args=[weakref.proxy(self)])
            self.poll_thread.start()
            retval = self.home(False) # TODO: Remove blocking while homing in INIT
            if retval != 0 and retval != 39:
                raise RuntimeError('Motor %s: Could not home, error %s'%(self.serial, err_codes[retval]))

        # SCC Methods
        def _Open(self, pollingIntervalMs: int = 100) -> bool:
            """Open connection to the KST101 Controller.

            Raises:
                RuntimeError: Connection to device is already open.
                RuntimeError: Error opening connection to device.

            Returns:
                bool: _description_
            """
            if int(self.serial) in Thorlabs.KST101.open_devices:
                raise RuntimeError('Device %d is already open.'%(int(self.serial)))
            ret = TLI_KST.Open(self.serial)
            if ret:
                raise RuntimeError('KST101:%s(): %d (%s)'%(__funcname__(), ret, err_codes[ret]))
            Thorlabs.KST101.open_devices.append(int(self.serial))
            self.open = True
            # Run self connection test.
            # ret = self._CheckConnection(self.serial)
            ret = self._CheckConnection()
            if ret == False:
                self._Close()
                raise RuntimeError('Device opened but connection test failed.')
            self._StartPolling(pollingIntervalMs)
            return True

        def __del__(self):
            if self.poll_thread is not None:
                self.keep_polling = False
                self._StopPolling()
                with self.cond:
                    self.cond.notify_all()
                self.poll_thread.join()
            if self.open:
                self._Close()
        
        def _Close(self) -> None:
            """Close connection to the KST101 Controller.
            """
            self._StopPolling()
            TLI_KST.Close(self.serial)
            Thorlabs.KST101.open_devices.remove(int(self.serial))
            self.serial = None
            self.open = False

        def _CheckConnection(self) -> bool:
            """Check connection to the device.

            Returns:
                bool: True if the device is connected.
            """
            return TLI_KST.CheckConnection(self.serial)
        
        def _Identify(self) -> None:
            """Identify the device by blinking the display backlight.

            Raises:
                RuntimeWarning: Connection to device is not open.

            Returns:
                None
            """
            if not self.open:
                self.Open()
            TLI_KST.Identify(self.serial)
            return
        
        # Should this be automatically performed on open?
        def _GetHardwareInfo(self) -> dict:
            """Get the hardware information for this device.

            Raises:
                RuntimeError: GetHardwareInfoBlock call fails
            
            Returns:
                dict: Information in struct TLI_HardwareInformation
            """
            if not self.open:
                self.Open()
            # ffi = FFI()
            # ffi.cdef("""
            # struct TLI_HardwareInformation
            # {
            #     DWORD serialNumber;
            #     char modelNumber[8];
            #     WORD type;
            #     DWORD firmwareVersion;
            #     char notes[48];
            #     unsigned char deviceDependantData[12];
            #     WORD hardwareVersion;
            #     WORD modificationState;
            #     short numChannels;};
            # """)
            ser_buf = package_ffi.new('struct TLI_HardwareInformation *')
            ret = TLI_KST.GetHardwareInfoBlock(self.serial, ser_buf)
            if ret:
                raise RuntimeError('KST101:%s(): %d (%s)'%(__funcname__(), ret, err_codes[ret]))
            return cdata_dict(ser_buf, package_ffi)

        def _StartPolling(self, rate_ms: int):
           ret = TLI_KST.StartPolling(self.serial, rate_ms)
           return ret

        def _StopPolling(self):
            ret = TLI_KST.StopPolling(self.serial)
            return ret

        def _WaitFor(self) -> tuple:
            mtype = package_ffi.new("WORD[1]")
            mid = package_ffi.new("WORD[1]")
            mdata = package_ffi.new("DWORD[1]")
            ret = TLI_KST.WaitForMessage(self.serial, mtype, mid, mdata)
            self.dev_mtype = int(mtype[0])
            self.dev_mid = int(mid[0])
            self.dev_mdata = int(mdata[0])
            # print('%s: %d: mtype: %d, mid: %d, mdata: %d'%(__funcname__(), ret, int(mtype[0]), int(mid[0]), int(mdata[0])))
            return (ret, int(mtype[0]), int(mid[0]), int(mdata[0]))

        def _GetNext(self) -> tuple:
            mtype = package_ffi.new("WORD[1]")
            mid = package_ffi.new("WORD[1]")
            mdata = package_ffi.new("DWORD[1]")
            ret = TLI_KST.GetNextMessage(self.serial, mtype, mid, mdata)
            self.dev_mtype = int(mtype[0])
            self.dev_mid = int(mid[0])
            self.dev_mdata = int(mdata[0])
            # print('%s: %d: mtype: %d, mid: %d, mdata: %d'%(__funcname__(), ret, int(mtype[0]), int(mid[0]), int(mdata[0])))
            return (ret, int(mtype[0]), int(mid[0]), int(mdata[0]))

        # Callable API functions.
        # API calls; possible examples.

        def set_stage(self, stype: str):
            if stype not in KST_Stages:
                raise RuntimeError('%s not a valid stage type'%(stype))
            self._mm_to_idx = Thorlabs.KST101.avail_stages[stype]
            ret = TLI_KST.SetStageType(self.serial, KST_Stages.index(stype))
            return ret

        @property
        def mm_to_idx(self):
            return self._mm_to_idx

        def wait_for(self, mtype: str, mid: str) -> bool:
            if mtype not in KST_MessageType.keys():
                raise RuntimeError('%s not a valid message type'%(mtype))
            if mid not in KST_MessageId[mtype].keys():
                raise RuntimeError('%s not a valid message id for device type %s'%(mid, mtype))
            ret = True
            TLI_KST.ClearMessageQueue(self.serial)
            while ret:
                ret, _mtype, _mid, _mdata = self._WaitFor()
                if ret == False:
                    return False
                if _mtype == KST_MessageType[mtype] and _mid == KST_MessageId[mtype][mid]:
                    break
            return ret

        @staticmethod
        def poll_status(arg):
            TLI_KST.ClearMessageQueue(arg.serial)
            while arg.keep_polling:
                # print('Poll thread: waiting')
                if arg.message_queue_size():
                    ret, _mtype, _mid, _mdata = arg._GetNext()
                    if not ret:
                        print('WARNING: did not get message in thread')
                        continue
                    if _mtype == KST_MessageType['GenericMotor']:
                        if arg.moving and ((_mid == KST_MessageId['GenericMotor']['Moved']) or (_mid == KST_MessageId['GenericMotor']['Stopped'])):
                            arg.moving = False
                            print('Poll: Stopped moving')
                            with arg.cond:
                                arg.cond.notify()
                        if arg.homing and (_mid == KST_MessageId['GenericMotor']['Moved']):
                            arg.homing = False
                            print('Poll: Stopped homing')
                            with arg.cond:
                                arg.cond.notify()
                        if arg.homing and (_mid == KST_MessageId['GenericMotor']['Homed']):
                            print('Poll: Homed')
                            arg.homed = True
                            arg.homing = False
                            with arg.cond:
                                arg.cond.notify()
                else:
                    sleep(arg.poll_interval) # polling interval

        def wait_for_move(self):
            with self.cond:
                while self.moving:
                    self.cond.wait()

        def wait_for_home(self):
            with self.cond:
                while self.homing:
                    self.cond.wait()
        
        def state_motor_params(self):
            stepsPerRev = package_ffi.new("double *")
            gearBoxRatio = package_ffi.new("double *")
            pitch = package_ffi.new("double *")

            stepsPerRev[0] = -1
            gearBoxRatio[0] = -1
            pitch[0] = -1

            err = TLI_KST.GetMotorParamsExt(self.serial, stepsPerRev, gearBoxRatio, pitch)
            print("Err: " + str(err) + "; StepsPerRev: " + str(stepsPerRev[0]) + ", GearBoxRatio: " + str(gearBoxRatio[0]) + ", Pitch: " + str(pitch[0]))

        def state_motor_velocity_limits(self):
            maxVelocity = package_ffi.new("double *")
            maxAcceleration = package_ffi.new("double *")

            err = TLI_KST.GetMotorVelocityLimits(self.serial, maxVelocity, maxAcceleration)
            print("Err: " + str(err) + "; MaxVelocity: " + str(maxVelocity[0]) + ", MaxAcceleration: " + str(maxAcceleration[0]))

        def state_motor_travel_limits(self):
            minPosition = package_ffi.new("double *")
            maxPosition = package_ffi.new("double *")

            err = TLI_KST.GetMotorTravelLimits(self.serial, minPosition, maxPosition)
            print("Err: " + str(err) + "; MinPosition: " + str(minPosition[0]) + ", MaxPosition: " + str(maxPosition[0]))

        def state_motor_travel_mode(self):
            print("Travel mode (see: MOT_TravelModes): " + str(TLI_KST.GetMotorTravelMode(self.serial)))

        def state_stage_axis_max_pos(self):
            print("Stage Max Pos: " + str(TLI_KST.GetStageAxisMaxPos(self.serial)))

        def state_stage_axis_min_pos(self):
            print("Stage Min Pos: " + str(TLI_KST.GetStageAxisMinPos(self.serial)))

        def message_queue_size(self):
            return TLI_KST.MessageQueueSize(self.serial)

        # get_status_n
        # get_status
        def get_status(self):
            pass

        # wait_for_status
        def wait_for_status(self):
            pass

        # home
        def home(self, blocking = False):
            retval = TLI_KST.Home(self.serial)
            # print('Home fcn: retval %d'%(retval))
            self.homing = True
            if blocking:
                self.wait_for_home()
            return retval

        # is_homing
        def is_homing(self):
            return self.homing

        # is_homed
        def is_homed(self):
            return self.homed

        # get_position
        def get_position(self):
            # TLI_KST.RequestPosition(self.serial)
            retval = TLI_KST.GetPosition(self.serial)
            return retval

        # set_position_reference
        def set_position_reference():
            pass

        # move_by
        def move_by(self, difference: int, block: bool):
            self.moving = True
            retval = TLI_KST.MoveRelative(self.serial, difference)
            if block:
                self.wait_for_move()
                # self.wait_for('GenericMotor', 'Moved')
            return retval

        # move_to
        def move_to(self, position: int, block: bool):
            self.moving = True
            retval = TLI_KST.MoveToPosition(self.serial, position)
            if block:
                self.wait_for_move()
            return retval

        # jog - probably slew?
        def jog(self, stepsize, direction):
            TLI_KST.SetJogStepSize(self.serial, stepsize)
            if direction == 'forward' or direction == 'forwards':
                _direction = MOT_TravelDirection[1]
            elif direction == 'backward' or direction == 'backwards':
                _direction = MOT_TravelDirection[2]
            else:
                _direction = MOT_TravelDirection[0]
            retval = TLI_KST.MoveJog(self.serial, _direction)
            return retval
        @staticmethod
        def get_message_fcn(obj, mtype, mid):
            pass

        def stop_polling(self):
            self._StopPolling()
            if self.poll_thread is not None:
                self.keep_polling = False
                with self.cond:
                    self.cond.notify_all()    
                self.poll_thread.join()
                self.poll_thread = None


        # is_moving
        def is_moving(self):
            return self.moving

        # wait_move
        # Needs some kind of condition.
        def wait_move(self):
            pass

        # stop
        def stop(self):
            retval = TLI_KST.StopProfiled(self.serial)
            return retval

        def emergency_stop(self):
            retval = TLI_KST.StopImmediate(self.serial)
            return retval

        # wait_for_stop
        def wait_for_stop(self):
            pass

        # get_velocity_parameters
        def get_velocity_parameters(self):
            pass

        # setup_velocity
        def setup_velocity(self):
            pass

        # get_jog_parameters
        def get_jog_parameters(self):
            pass

        # setup_jog
        def setup_jog(self):
            pass

        # get_homing_parameters
        def get_homing_parameters(self):
            pass

        # setup_homing
        def setup_homing(self):
            pass

        # get_gen_move_parameters
        def get_gen_move_parameters(self):
            pass

        # setup_gen_move
        def setup_gen_move(self):
            pass

        # get_limit_switch_parameters
        def get_limit_switch_parameters(self):
            pass

        # setup_limit_switch
        def setup_limit_switch(self):
            pass

        # get_kcube_trigio_parameters
        def get_kcube_trigio_parameters(self):
            pass

        # setup_kcube_trigio
        def setup_kcube_trigio(self):
            pass

        # get_kcube_trigpos_parameters
        def get_kcube_trigpos_parameters(self):
            pass

        # setup_kcube_trigpos
        def setup_kcube_trigpos(self):
            pass

    class KSTDummy: # Subclass for KST101 devices
        # API calls; possible examples.
        """
            get_status_n
            get_status
            wait_for_status

            home
            is_homing
            is_homed
            wait_for_home

            get_position
            set_position_reference
            move_by
            move_to
            jog
            is_moving
            wait_move
            stop
            wait_for_stop

            get_velocity_parameters
            setup_velocity
            get_jog_parameters
            setup_jog
            get_homing_parameters
            setup_homing
            get_gen_move_parameters
            setup_gen_move
            get_limit_switch_parameters
            setup_limit_switch
            get_kcube_trigio_parameters
            setup_kcube_trigio
            get_kcube_trigpos_parameters
            setup_kcube_trigpos
        """
        # TLI List method
        open_devices = [] # List of opened devices

        avail_stages = {}
        avail_stages['ZST25'] = 2184560.64
        @staticmethod
        def _ListDevices() -> list:
            """List all available KST101 devices (including opened devices).

            Returns:
                list: Serial numbers of available KST101 devices.

            NOTE: Backport listing opened devices feature to Thorlabs.ListDevicesAny() and Thorlabs.ListDevices()
            """
            return [2600001]
        
        # Init stores the serial number
        def __init__(self, serialNumber: int, pollingIntervalMs: int = 100): # should also get the stage here
            """Create an instance of Thorlabs KST101 Stepper Motor Controller

            Args:
                serialNumber (int): Serial number of the KST101 Controller

            Raises:
                ValueError: Invalid serial number
                RuntimeError: Instance of KST101 exists with this serial number
                RuntimeError: Serial number not in device list
            """
            self.poll_thread = None
            if str(serialNumber)[:2] != str(Thorlabs.TYPE_KST101):
                raise ValueError('Invalid serial %d: KST101 Serial starts with %s'%(serialNumber, str(Thorlabs.TYPE_KST101)))
            elif serialNumber in Thorlabs.KSTDummy.open_devices:
                raise RuntimeError('Serial %d already in use.'%(serialNumber))
            elif serialNumber not in Thorlabs.KSTDummy._ListDevices():
                raise RuntimeError('Serial %d not in device list.'%(serialNumber))
            self.serial = str(serialNumber)
            self.position = 123
            self.open = False
            self._Open(pollingIntervalMs)
            self.moving = False
            self.homed = False
            self.homing = False
            self._mm_to_idx = 0
            self.keep_polling = True
            self.poll_interval = pollingIntervalMs * 0.001
            self.mutex = threading.Lock()
            self.cond = threading.Condition(self.mutex)
            self.poll_thread = threading.Thread(target = Thorlabs.KSTDummy.poll_status, args=[weakref.proxy(self)])
            self.poll_thread.start()
            retval = self.home(False) # TODO: Remove blocking while homing in INIT
            if retval != 0 and retval != 39:
                raise RuntimeError('Motor %s: Could not home, error %s'%(self.serial, err_codes[retval]))

        # SCC Methods
        def _Open(self, pollingIntervalMs: int = 100) -> bool:
            """Open connection to the KST101 Controller.

            Raises:
                RuntimeError: Connection to device is already open.
                RuntimeError: Error opening connection to device.

            Returns:
                bool: _description_
            """
            if int(self.serial) in Thorlabs.KSTDummy.open_devices:
                raise RuntimeError('Device %d is already open.'%(int(self.serial)))
            Thorlabs.KSTDummy.open_devices.append(int(self.serial))
            self.open = True
            # Run self connection test.
            return True

        def __del__(self):
            if self.poll_thread is not None:
                self.keep_polling = False
                self._StopPolling()
                with self.cond:
                    self.cond.notify_all()
                self.poll_thread.join()
            if self.open:
                self._Close()
        
        def _Close(self) -> None:
            """Close connection to the KST101 Controller.
            """
            Thorlabs.KSTDummy.open_devices.remove(int(self.serial))
            self.serial = None
            self.open = False

        def _CheckConnection(self) -> bool:
            """Check connection to the device.

            Returns:
                bool: True if the device is connected.
            """
            return True
        
        def _Identify(self) -> None:
            """Identify the device by blinking the display backlight.

            Raises:
                RuntimeWarning: Connection to device is not open.

            Returns:
                None
            """
            return
        
        # Should this be automatically performed on open?
        def _GetHardwareInfo(self) -> dict:
            """Get the hardware information for this device.

            Raises:
                RuntimeError: GetHardwareInfoBlock call fails
            
            Returns:
                dict: Information in struct TLI_HardwareInformation
            """

            retdict = {}
            retdict['serialNumber'] = 2600001
            retdict['modelNumber'] = 'KSTDum'
            retdict['type'] = None
            retdict['firmwareVersion'] = None
            retdict['notes'] = None
            retdict['deviceDependantData'] = None
            retdict['hardwareVersion'] = None
            retdict['modificationState'] = None
            retdict['numChannels'] = None

            # ffi = FFI()
            # ffi.cdef("""
            # struct TLI_HardwareInformation
            # {
            #     DWORD serialNumber;
            #     char modelNumber[8];
            #     WORD type;
            #     DWORD firmwareVersion;
            #     char notes[48];
            #     unsigned char deviceDependantData[12];
            #     WORD hardwareVersion;
            #     WORD modificationState;
            #     short numChannels;};
            # """)
            
            return retdict

        def _StartPolling(self, rate_ms: int):
            return True

        def _StopPolling(self):
            return True

        def _WaitFor(self) -> tuple:
            return (0,0,0,0)

        def _GetNext(self) -> tuple:
            return (0,0,0,0)

        # Callable API functions.
        # API calls; possible examples.

        def set_stage(self, stype: str):
            self._mm_to_idx = Thorlabs.KST101.avail_stages[stype]
            return True

        @property
        def mm_to_idx(self):
            return self._mm_to_idx

        def wait_for(self, mtype: str, mid: str) -> bool:
            return True

        @staticmethod
        def poll_status(arg):
            while arg.keep_polling:
                # print('Poll thread: waiting')
                if arg.moving:
                    sleep(0.5)
                    arg.moving = False
                    with arg.cond:
                        arg.cond.notify()
                elif arg.homing:
                    sleep(0.5)
                    arg.homing = False
                    arg.homed = True
                    with arg.cond:
                        arg.cond.notify()
                else:
                    sleep(arg.poll_interval) # polling interval

        def wait_for_move(self):
            with self.cond:
                while self.moving:
                    self.cond.wait()

        def wait_for_home(self):
            with self.cond:
                while self.homing:
                    self.cond.wait()
        
        def state_motor_params(self):
            return

        def state_motor_velocity_limits(self):
            return

        def state_motor_travel_limits(self):
            return

        def state_motor_travel_mode(self):
            return

        def state_stage_axis_max_pos(self):
            return

        def state_stage_axis_min_pos(self):
            return

        def message_queue_size(self) -> int:
            return 0

        # get_status_n
        # get_status
        def get_status(self):
            pass

        # wait_for_status
        def wait_for_status(self):
            pass

        # home
        def home(self, blocking = False):
            # print('Home fcn: retval %d'%(retval))
            self.position = 0
            self.homing = True
            if blocking:
                self.wait_for_home()
            return self.homed

        # is_homing
        def is_homing(self):
            return self.homing

        # is_homed
        def is_homed(self):
            return self.homed

        # get_position
        def get_position(self):
            # TLI_KST.RequestPosition(self.serial)
            retval = self.position
            return retval

        # set_position_reference
        def set_position_reference():
            pass

        # move_by
        def move_by(self, difference: int, block: bool):
            self.moving = True
            self.position += difference
            if block:
                self.wait_for_move()
                # self.wait_for('GenericMotor', 'Moved')
            return True

        # move_to
        def move_to(self, position: int, block: bool):
            self.moving = True
            self.position = position
            if block:
                self.wait_for_move()
            return True

        # jog - probably slew?
        def jog(self, stepsize, direction):
            return 0
        @staticmethod
        def get_message_fcn(obj, mtype, mid):
            pass

        def stop_polling(self):
            self._StopPolling()
            if self.poll_thread is not None:
                self.keep_polling = False
                with self.cond:
                    self.cond.notify_all()    
                self.poll_thread.join()
                self.poll_thread = None


        # is_moving
        def is_moving(self):
            return self.moving

        # wait_move
        # Needs some kind of condition.
        def wait_move(self):
            pass

        # stop
        def stop(self):
            return 0
            return retval

        def emergency_stop(self):
            return 0
            return retval

        # wait_for_stop
        def wait_for_stop(self):
            pass

        # get_velocity_parameters
        def get_velocity_parameters(self):
            pass

        # setup_velocity
        def setup_velocity(self):
            pass

        # get_jog_parameters
        def get_jog_parameters(self):
            pass

        # setup_jog
        def setup_jog(self):
            pass

        # get_homing_parameters
        def get_homing_parameters(self):
            pass

        # setup_homing
        def setup_homing(self):
            pass

        # get_gen_move_parameters
        def get_gen_move_parameters(self):
            pass

        # setup_gen_move
        def setup_gen_move(self):
            pass

        # get_limit_switch_parameters
        def get_limit_switch_parameters(self):
            pass

        # setup_limit_switch
        def setup_limit_switch(self):
            pass

        # get_kcube_trigio_parameters
        def get_kcube_trigio_parameters(self):
            pass

        # setup_kcube_trigio
        def setup_kcube_trigio(self):
            pass

        # get_kcube_trigpos_parameters
        def get_kcube_trigpos_parameters(self):
            pass

        # setup_kcube_trigpos
        def setup_kcube_trigpos(self):
            pass

# %%
if __name__ == '__main__':
    from pprint import pprint

    serials = Thorlabs.ListDevicesAny()
    print('Serial number(s): ', end = '')
    pprint(serials)
    devinfo = Thorlabs.GetDeviceInfo(serials[0])
    print('Device Info: ', end = '')
    pprint(devinfo)
    print('Device Info(s): ', end = '')
    pprint(Thorlabs.GetDeviceInfo(serials))
    
    print("INITIALIZING DEVICE")
    motor_ctrl = Thorlabs.KST101(serials[0])
    sleep(1)
    
    print("LISTING DEVICES: ")
    print(motor_ctrl._ListDevices())
    sleep(1)    

    # print(motor_ctrl.Open())
    # print(motor_ctrl.GetHardwareInfo())
    # motor_ctrl.Identify()
    
    print('Connection status: ' + str(motor_ctrl._CheckConnection()))
    sleep(1)

    # print('Backlight on device should now blink for 5 seconds...')
    # motor_ctrl._Identify()

    print('Current position: ' + str(motor_ctrl.get_position()))
    sleep(1)

    print("Getting Motor Data:")
    motor_ctrl.state_motor_params()
    sleep(1)
    motor_ctrl.state_motor_velocity_limits()
    sleep(1)
    motor_ctrl.state_motor_travel_limits()
    sleep(1)
    motor_ctrl.state_motor_travel_mode()
    sleep(1)
    motor_ctrl.state_stage_axis_max_pos()
    sleep(1)
    motor_ctrl.state_stage_axis_min_pos()
    sleep(1)
    
    print("Inbox:", motor_ctrl.message_queue_size())

    if (motor_ctrl.message_queue_size() > 0):
        print("You've got mail!")
    else:
        print("No messages in queue.")

    # motor_ctrl.home()
    print(motor_ctrl.set_stage('ZST25'))
    print("ATTEMPTING TO MOVE")

    # MM_TO_NM = 10e6
    # MM_TO_IDX = 2184532 # Based on motor/stage...
    MM_TO_IDX = 2184560.64 # 7471104

    # DESIRED_POSITION_NM = 0

    # order = 1
    # zero_order_offset = 1
    # L = 550
    # grating_density = 0.0012
    # dX = DESIRED_POSITION_NM
    # a = ((2) * (1 / grating_density) * dcos(32) * ((dX + zero_order_offset)/(L)) * (MM_TO_NM)) / (order)
    # print("a: " + str(a))

    DESIRED_POSITION_MM = 5

    # DESIRED_POSITION_MM = int((DESIRED_POSITION_NM  ) + 1)
    DESIRED_POSITION_IDX = int(DESIRED_POSITION_MM * MM_TO_IDX)
    # retval = motor_ctrl.move_to(DESIRED_POSITION_IDX, True)
    retval = motor_ctrl.move_to(DESIRED_POSITION_IDX, True)
    # sleep(1)

    # if (retval == 0):
    #     while True:
    #         currpos = int(motor_ctrl.get_position())
    #         if (currpos == DESIRED_POSITION_IDX):
    #             print("At desired position.")
    #             break
    #         else:
    #             print("Moving... (" + str(currpos) + ")")
    #         sleep(1)
    # else:
    #     print("Moving error (" + str(retval) + ").")

    print('Final position: ' + str(motor_ctrl.get_position()))
    print("Press any key for next move...")
    input()
    retval = motor_ctrl.move_by(DESIRED_POSITION_IDX * 2, True) # another 10 mm
    print("Press any key to exit...")
    input()

    # print('Move by retval: ' + str(motor_ctrl.move_by(100)))

    del motor_ctrl
# %%