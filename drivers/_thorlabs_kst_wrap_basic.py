#
# @file _thorlabs_kst_wrap_basic.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Mid-level ThorLabs KST driver wrapper.
# @version See Git tags for version information.
# @date 2022.08.18
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

# Imports
from __future__ import annotations
from nicelib import load_lib, NiceLib, Sig, NiceObject, RetHandler, ret_ignore, LibInfo
from cffi import FFI
from inspect import getmembers
import warnings
from time import sleep
import math as m

from . import _thorlabs_kst_lib

def dcos(deg):
    return m.degrees((m.cos(m.radians(32))))
    
# Get current function name
def __funcname__():
    import inspect
    return inspect.stack()[1][3]

# Return value strings
err_codes = [
    'Success',
    'FT_InvalidHandle - The FTDI functions have not been initialized',
    'FT_DeviceNotFound - The Device could not be found',
    'FT_DeviceNotOpened - The Device must be opened before it can be accessed',
    'FT_IOError - An I/O Error has occured in the FTDI chip',
    'FT_InsufficientResources - There are Insufficient resources to run this application',
    'FT_InvalidParameter - An invalid parameter has been supplied to the device',
    'FT_DeviceNotPresent - The Device is no longer present',
    'FT_IncorrectDevice - The device detected does not match that expected'
]
# Enums
FT_Status = [
    'FT_OK',
    'FT_InvalidHandle',
    'FT_DeviceNotFound',
    'FT_DeviceNotOpened',
    'FT_IOError',
    'FT_InsufficientResources',
    'FT_InvalidParameter',
    'FT_DeviceNotPresent',
    'FT_IncorrectDevice'
]
MOT_MotorTypes = [
    'MOT_NotMotor',
    'MOT_DCMotor',
    'MOT_StepperMotor',
    'MOT_BrushlessMotor',
    'MOT_CustomMotor'
] 
MOT_TravelModes = [
    'MOT_TravelModeUndefined',
    'MOT_Linear',
    'MOT_Rotational'
]
MOT_TravelDirection = [
    'MOT_TravelDirectionUndefined',
    'MOT_Forwards',
    'MOT_Backwards',
]
KST_Stages = [
    'ZST6',
    'ZST13',
    'ZST25',
    'ZST206',
    'ZST213',
    'ZST225',
    'ZFS206',
    'ZFS213',
    'ZFS225',
    'DRV013_25MM',
    'DRV014_50MM',
    'NR360',
    'PLS_X25MM',
    'PLS_X25MM_HiRes',
    'FW103'
]
MOT_HomeLimitSwitchDirection = [
    'MOT_LimitSwitchDirectionUndefined',
    'MOT_ReverseLimitSwitch',
    'MOT_ForwardLimitSwitch'
]
MOT_DirectionSense = [
    'MOT_Normal',
    'MOT_Reverse'
]
MOT_JogModes = [
    'MOT_JogModeUndefined',
    'MOT_Continuous',
    'MOT_SingleStep',
]
MOT_StopModes = [
    'MOT_StopModeUndefined',
    'MOT_Immediate',
    'MOT_Profiled'
]
MOT_LimitSwitchModes = [
    'MOT_LimitSwitchModeUndefined',
    'MOT_LimitSwitchIgnoreSwitch',
    'MOT_LimitSwitchMakeOnContact',
    'MOT_LimitSwitchBreakOnContact',
    'MOT_LimitSwitchMakeOnHome',
    'MOT_LimitSwitchBreakOnHome',
    'MOT_PMD_Reserved',
    'MOT_LimitSwitchIgnoreSwitchSwapped',
    'MOT_LimitSwitchMakeOnContactSwapped',
    'MOT_LimitSwitchBreakOnContactSwapped',
    'MOT_LimitSwitchMakeOnHomeSwapped',
    'MOT_LimitSwitchBreakOnHomeSwapped'
]
MOT_LimitSwitchSWModes = [
    'MOT_LimitSwitchSWModeUndefined',
    'MOT_LimitSwitchIgnored',
    'MOT_LimitSwitchStopImmediate',
    'MOT_LimitSwitchStopProfiled',
    'MOT_LimitSwitchIgnored_Rotational',
    'MOT_LimitSwitchStopImmediate_Rotational',
    'MOT_LimitSwitchStopProfiled_Rotational'
]
MOT_LimitsSoftwareApproachPolicy = [
    'DisallowIllegalMoves',
    'AllowPartialMoves',
    'AllowAllMoves'
]
KMOT_WheelDirectionSense = [
    'KMOT_WM_Positive',
    'KMOT_WM_Negative'
]
KMOT_WheelMode = [
    'KMOT_WM_Velocity',
    'KMOT_WM_Jog',
    'KMOT_WM_MoveAbsolute'
]
KMOT_TriggerPortMode = [
    'KMOT_TrigDisabled',
    'KMOT_TrigIn_GPI',
    'KMOT_TrigIn_RelativeMove',
    'KMOT_TrigIn_AbsoluteMove',
    'KMOT_TrigIn_Home',
    'KMOT_TrigIn_Stop',
    'KMOT_TrigOut_GPO',
    'KMOT_TrigOut_InMotion',
    'KMOT_TrigOut_AtMaxVelocity',
    'KMOT_TrigOut_AtPositionSteps',
    'KMOT_TrigOut_Synch'
]
KMOT_TriggerPortPolarity = [
    'KMOT_TrigPolarityHigh',
    'KMOT_TrigPolarityLow'
]
MOT_PID_LoopMode = [
    'MOT_PIDLoopModeDisabled',
    'MOT_PIDOpenLoopMode',
    'MOT_PIDClosedLoopMode'
]
MOT_MovementModes = [
    'LinearRange',
    'RotationalUnlimited',
    'RotationalWrapping'
]
MOT_MovementDirections = [
    'Quickest',
    'Forwards',
    'Reverse'
]

KST_MessageType = {
    'GenericDevice': 0,
    'GenericPiezo': 1,
    'GenericMotor': 2,
    'GenericDCMotor': 3,
    'GenericSimpleMotor': 4,
    'RackDevice': 5,
    'Laser': 6,
    'TECCtlr': 7,
    'Quad': 8,
    'NanoTrak': 9,
    'Specialized': 10,
    'Solenoid': 11,
    'InertialMotorCtlr': 12,
    'LiquidCrystalCtlr': 13
}

# if KST_MessageType[] key not in KST_MessageId, not implemented

KST_MessageId = {
    'GenericDevice': {'settingsInitialized': 0, 'settingsUpdated': 1, 'settingsExtern': 2, 'error': 3, 'close': 4, 'settingsReset': 5},
    'GenericMotor': {'Homed': 0, 'Moved': 1, 'Stopped': 2, 'LimitUpdated': 3}
}


# Return Handler Example
@RetHandler(num_retvals=0)
def ret_errcode(retval):
    return retval

# Converting struct to Dictionary
def cdata_dict(cd, ffi: FFI):
    if isinstance(cd, ffi.CData):
        try:
            return ffi.string(cd).decode('utf-8')
        except TypeError:
            try:
                return [cdata_dict(x, ffi) for x in cd]
            except TypeError:
                return {k: cdata_dict(v, ffi) for k, v in getmembers(cd)}
    else:
        return cd

# Struct definitions.
package_ffi = FFI()

# Define enums.
package_ffi.cdef('typedef enum {FT_OK, FT_InvalidHandle, FT_DeviceNotFound, FT_DeviceNotOpened, FT_IOError, FT_InsufficientResources, FT_InvalidParameter, FT_DeviceNotPresent, FT_IncorrectDevice} FT_Status;')
package_ffi.cdef('typedef enum {MOT_NotMotor, MOT_DCMotor, MOT_StepperMotor, MOT_BrushlessMotor, MOT_CustomMotor} MOT_MotorTypes;')
package_ffi.cdef('typedef enum {MOT_TravelModeUndefined, MOT_Linear, MOT_Rotational} MOT_TravelModes;')
package_ffi.cdef('typedef enum {MOT_TravelDirectionUndefined, MOT_Forwards, MOT_Backwards} MOT_TravelDirection;')
package_ffi.cdef('typedef enum {ZST6, ZST13, ZST25, ZST206, ZST213, ZST225, ZFS206, ZFS213, ZFS225, DRV013_25MM, DRV014_50MM, NR360, PLS_X25MM, PLS_X25MM_HiRes, FW103} KST_Stages;')
package_ffi.cdef('typedef enum {MOT_LimitSwitchDirectionUndefined, MOT_ReverseLimitSwitch, MOT_ForwardLimitSwitch} MOT_HomeLimitSwitchDirection;')
package_ffi.cdef('typedef enum {MOT_Normal, MOT_Reverse} MOT_DirectionSense;')
package_ffi.cdef('typedef enum {MOT_JogModeUndefined, MOT_Continuous, MOT_SingleStep} MOT_JogModes;')
package_ffi.cdef('typedef enum {MOT_StopModeUndefined, MOT_Immediate, MOT_Profiled} MOT_StopModes;')
package_ffi.cdef('typedef enum {MOT_LimitSwitchModeUndefined, MOT_LimitSwitchIgnoreSwitch, MOT_LimitSwitchMakeOnContact, MOT_LimitSwitchBreakOnContact, MOT_LimitSwitchMakeOnHome, MOT_LimitSwitchBreakOnHome, MOT_PMD_Reserved, MOT_LimitSwitchIgnoreSwitchSwapped, MOT_LimitSwitchMakeOnContactSwapped, MOT_LimitSwitchBreakOnContactSwapped, MOT_LimitSwitchMakeOnHomeSwapped, MOT_LimitSwitchBreakOnHomeSwapped} MOT_LimitSwitchModes;')
package_ffi.cdef('typedef enum {MOT_LimitSwitchSWModeUndefined, MOT_LimitSwitchIgnored, MOT_LimitSwitchStopImmediate, MOT_LimitSwitchStopProfiled, MOT_LimitSwitchIgnored_Rotational, MOT_LimitSwitchStopImmediate_Rotational, MOT_LimitSwitchStopProfiled_Rotational} MOT_LimitSwitchSWModes;')
package_ffi.cdef('typedef enum {DisallowIllegalMoves, AllowPartialMoves, AllowAllMoves} MOT_LimitsSoftwareApproachPolicy;')
package_ffi.cdef('typedef enum {KMOT_WM_Positive, KMOT_WM_Negative} KMOT_WheelDirectionSense;')
package_ffi.cdef('typedef enum {KMOT_WM_Velocity, KMOT_WM_Jog, KMOT_WM_MoveAbsolute} KMOT_WheelMode;')
package_ffi.cdef('typedef enum {KMOT_TrigDisabled, KMOT_TrigIn_GPI, KMOT_TrigIn_RelativeMove, KMOT_TrigIn_AbsoluteMove, KMOT_TrigIn_Home, KMOT_TrigIn_Stop, KMOT_TrigOut_GPO, KMOT_TrigOut_InMotion, KMOT_TrigOut_AtMaxVelocity, KMOT_TrigOut_AtPositionSteps, KMOT_TrigOut_Synch} KMOT_TriggerPortMode;')
package_ffi.cdef('typedef enum {KMOT_TrigPolarityHigh, KMOT_TrigPolarityLow} KMOT_TriggerPortPolarity;')
package_ffi.cdef('typedef enum {MOT_PIDLoopModeDisabled, MOT_PIDOpenLoopMode, MOT_PIDClosedLoopMode} MOT_PID_LoopMode;')
package_ffi.cdef('typedef enum {LinearRange, RotationalUnlimited, RotationalWrapping} MOT_MovementModes;')
package_ffi.cdef('typedef enum {Quickest, Forwards, Reverse} MOT_MovementDirections;')

# Define structs.
package_ffi.cdef("""
typedef struct TLI_DeviceInfo
{
   DWORD typeID;
   char description[65];
   char serialNo[16];
   DWORD PID;
   bool isKnownType;
   MOT_MotorTypes motorType;
   bool isPiezoDevice;
   bool isLaser;
   bool isCustomType;
   bool isRack;
   short maxChannels;
} TLI_DeviceInfo;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct TLI_HardwareInformation
{
   DWORD serialNumber;
   char modelNumber[8];
   WORD type;
   DWORD firmwareVersion;
   char notes[48];
   BYTE deviceDependantData[12];
   WORD hardwareVersion;
   WORD modificationState;
   short numChannels;
} TLI_HardwareInformation;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct MOT_VelocityParameters
{
   int minVelocity;
   int acceleration;
   int maxVelocity;
} MOT_VelocityParameters;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct MOT_JogParameters
{
   MOT_JogModes mode;
   unsigned int stepSize;
   MOT_VelocityParameters velParams;
   MOT_StopModes stopMode;
} MOT_JogParameters;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct MOT_HomingParameters
{
   MOT_TravelDirection direction;
   MOT_HomeLimitSwitchDirection limitSwitch;
   unsigned int velocity;
   unsigned int offsetDistance;
} MOT_HomingParameters;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct MOT_LimitSwitchParameters
{
   MOT_LimitSwitchModes clockwiseHardwareLimit;
   MOT_LimitSwitchModes anticlockwiseHardwareLimit;
   DWORD clockwisePosition;
   DWORD anticlockwisePosition;
   MOT_LimitSwitchSWModes softLimitMode;
} MOT_LimitSwitchParameters;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct MOT_PowerParameters
{
   WORD restPercentage;
   WORD movePercentage;
} MOT_PowerParameters;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct KMOT_MMIParams
{
   KMOT_WheelMode WheelMode;
   int WheelMaxVelocity;
   int WheelAcceleration;
   MOT_DirectionSense WheelDirectionSense;
   int PresetPos1;
   int PresetPos2;
   short DisplayIntensity;
   short DisplayTimeout;
   short DisplayDimIntensity;
   short reserved[4];
} KMOT_MMIParams;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct KMOT_TriggerConfig
{
   KMOT_TriggerPortMode Trigger1Mode;
   KMOT_TriggerPortPolarity Trigger1Polarity;
   KMOT_TriggerPortMode Trigger2Mode;
   KMOT_TriggerPortPolarity Trigger2Polarity;
   short reserved[6];
} KMOT_TriggerConfig;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct KMOT_TriggerParams
{
   int TriggerStartPositionFwd;
   int TriggerIntervalFwd;
   int TriggerPulseCountFwd;
   int TriggerStartPositionRev;
   int TriggerIntervalRev;
   int TriggerPulseCountRev;
   int TriggerPulseWidth;
   int CycleCount;
   int reserved[6];
} KMOT_TriggerParams;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct MOT_PIDLoopEncoderParams
{
   MOT_PID_LoopMode loopMode;
   int proportionalGain;
   int integralGain;
   int differentialGain;
   int PIDOutputLimit;
   int PIDTolerance;
} MOT_PIDLoopEncoderParams;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct tagSAFEARRAYBOUND
{
   ULONG cElements;
   LONG lLbound;
} SAFEARRAYBOUND;
""", packed=1) # Defines struct, with packing.

package_ffi.cdef("""
typedef struct tagSAFEARRAY
{
   USHORT cDims;
   USHORT fFeatures;
   ULONG cbElements;
   ULONG cLocks;
   PVOID pvData;
   SAFEARRAYBOUND rgsabound[ 1 ];
} SAFEARRAY;
""", packed=1) # Defines struct, with packing.

# TLI Functions
class TLIBase(NiceLib): # this would be the base of the Thorlabs namespace, which would provide static methods common across all Thorlabs sub APIs
    _info_ = LibInfo(_thorlabs_kst_lib) # load_lib('thorlabs_kst_')
    _ret_ = ret_errcode
    _prefix_ = 'TLI_'

    # Function list auto-generated by fn_convert.py.
    BuildDeviceList = Sig()
    GetDeviceListSize = Sig()
    GetDeviceList = Sig('out')
    GetDeviceListByType = Sig('out', 'in')
    GetDeviceListByTypes = Sig('out', 'in', 'in')
    GetDeviceListExt = Sig('in', 'in')
    GetDeviceListByTypeExt = Sig('in', 'in', 'in')
    GetDeviceListByTypesExt = Sig('in', 'in', 'in', 'in')
    GetDeviceInfo = Sig('in', 'in')
    InitializeSimulations = Sig(ret=ret_ignore)
    UninitializeSimulations = Sig(ret=ret_ignore)

class TLI_KST(NiceLib): # This would be KST101, a subclass of Thorlabs
    _info_ = LibInfo(_thorlabs_kst_lib) # load_lib('thorlabs_kst_')
    _prefix_ = 'SCC_'

    # Function list auto-generated by fn_convert.py.
    Open = Sig('in')
    Close = Sig('in', ret = ret_ignore)
    CheckConnection = Sig('in')
    Identify = Sig('in', ret = ret_ignore)
    SetStageType = Sig('in', 'in')
    GetHardwareInfoBlock = Sig('in', 'in') # ser, TLI_HardwareInformation
    GetSoftwareVersion = Sig('in')
    SetCalibrationFile = Sig('in', 'in', 'in', ret=ret_ignore)
    IsCalibrationActive = Sig('in')
    GetCalibrationFile = Sig('in', 'in', 'in')
    GetHubBay = Sig('in')
    LoadSettings = Sig('in')
    LoadNamedSettings = Sig('in', 'in')
    PersistSettings = Sig('in')
    DisableChannel = Sig('in')
    EnableChannel = Sig('in')
    # CanDeviceLockFrontPanel = Sig('in')
    # GetFrontPanelLocked = Sig('in')
    # RequestFrontPanelLocked = Sig('in')
    # SetFrontPanelLock = Sig('in', 'in')
    GetNumberPositions = Sig('in')
    MoveToPosition = Sig('in', 'in')
    GetPosition = Sig('in')
    CanHome = Sig('in')
    NeedsHoming = Sig('in')
    CanMoveWithoutHomingFirst = Sig('in')
    Home = Sig('in')
    ClearMessageQueue = Sig('in', ret=ret_ignore)
    RegisterMessageCallback = Sig('in', 'in', ret=ret_ignore)
    MessageQueueSize = Sig('in')
    GetNextMessage = Sig('in', 'in', 'in', 'in')
    WaitForMessage = Sig('in', 'in', 'in', 'in')
    RequestHomingParams = Sig('in')
    GetHomingVelocity = Sig('in')
    SetHomingVelocity = Sig('in', 'in')
    MoveRelative = Sig('in', 'in')
    RequestJogParams = Sig('in')
    GetJogMode = Sig('in', 'in', 'in')
    SetJogMode = Sig('in', 'in', 'in')
    GetJogStepSize = Sig('in')
    SetJogStepSize = Sig('in', 'in')
    GetJogVelParams = Sig('in', 'in', 'in')
    SetJogVelParams = Sig('in', 'in', 'in')
    MoveJog = Sig('in', 'in')
    RequestVelParams = Sig('in')
    GetVelParams = Sig('in', 'in', 'in')
    SetVelParams = Sig('in', 'in', 'in')
    MoveAtVelocity = Sig('in', 'in')
    SetDirection = Sig('in', 'in', ret=ret_ignore)
    StopImmediate = Sig('in')
    StopProfiled = Sig('in')
    RequestBacklash = Sig('in')
    GetBacklash = Sig('in')
    SetBacklash = Sig('in', 'in')
    GetPositionCounter = Sig('in')
    SetPositionCounter = Sig('in', 'in')
    RequestEncoderCounter = Sig('in')
    GetEncoderCounter = Sig('in')
    SetEncoderCounter = Sig('in', 'in')
    RequestLimitSwitchParams = Sig('in')
    GetLimitSwitchParams = Sig('in', 'in', 'in', 'in', 'in', 'in')
    SetLimitSwitchParams = Sig('in', 'in', 'in', 'in', 'in', 'in')
    GetSoftLimitMode = Sig('in')
    SetLimitsSoftwareApproachPolicy = Sig('in', 'in', ret=ret_ignore)
    RequestMMIParams = Sig('in')
    RequestTriggerConfigParams = Sig('in')
    GetTriggerConfigParams = Sig('in', 'in', 'in', 'in', 'in')
    SetTriggerConfigParams = Sig('in', 'in', 'in', 'in', 'in')
    RequestPosTriggerParams = Sig('in')
    GetTriggerConfigParamsBlock = Sig('in', 'in')
    SetTriggerConfigParamsBlock = Sig('in', 'in')
    GetTriggerParamsParamsBlock = Sig('in', 'in')
    SetTriggerParamsParamsBlock = Sig('in', 'in')
    GetVelParamsBlock = Sig('in', 'in')
    SetVelParamsBlock = Sig('in', 'in')
    RequestMoveAbsolutePosition = Sig('in')
    SetMoveAbsolutePosition = Sig('in', 'in')
    GetMoveAbsolutePosition = Sig('in')
    MoveAbsolute = Sig('in')
    RequestMoveRelativeDistance = Sig('in')
    SetMoveRelativeDistance = Sig('in', 'in')
    GetMoveRelativeDistance = Sig('in')
    MoveRelativeDistance = Sig('in')
    GetHomingParamsBlock = Sig('in', 'in')
    SetHomingParamsBlock = Sig('in', 'in')
    GetJogParamsBlock = Sig('in', 'in')
    SetJogParamsBlock = Sig('in', 'in')
    GetLimitSwitchParamsBlock = Sig('in', 'in')
    SetLimitSwitchParamsBlock = Sig('in', 'in')
    RequestPowerParams = Sig('in')
    GetPowerParams = Sig('in', 'in')
    SetPowerParams = Sig('in', 'in')
    RequestBowIndex = Sig('in')
    GetBowIndex = Sig('in')
    SetBowIndex = Sig('in', 'in')
    UsesPIDLoopEncoding = Sig('in')
    SetPIDLoopEncoderParams = Sig('in', 'in')
    SetPIDLoopEncoderCoeff = Sig('in', 'in')
    RequestPIDLoopEncoderParams = Sig('in')
    GetPIDLoopEncoderParams = Sig('in', 'in')
    GetPIDLoopEncoderCoeff = Sig('in')
    SuspendMoveMessages = Sig('in')
    ResumeMoveMessages = Sig('in')
    RequestPosition = Sig('in')
    RequestStatusBits = Sig('in')
    GetStatusBits = Sig('in')
    StartPolling = Sig('in', 'in')
    PollingDuration = Sig('in')
    StopPolling = Sig('in', ret=ret_ignore)
    TimeSinceLastMsgReceived = Sig('in', 'in')
    EnableLastMsgTimer = Sig('in', 'in', 'in', ret=ret_ignore)
    HasLastMsgTimerOverrun = Sig('in')
    RequestSettings = Sig('in')
    GetStageAxisMinPos = Sig('in')
    GetStageAxisMaxPos = Sig('in')
    SetStageAxisLimits = Sig('in', 'in', 'in')
    SetMotorTravelMode = Sig('in', 'in')
    GetMotorTravelMode = Sig('in')
    SetMotorParams = Sig('in', 'in', 'in', 'in')
    GetMotorParams = Sig('in', 'in', 'in', 'in')
    SetMotorParamsExt = Sig('in', 'in', 'in', 'in')
    GetMotorParamsExt = Sig('in', 'in', 'in', 'in')
    SetMotorVelocityLimits = Sig('in', 'in', 'in')
    GetMotorVelocityLimits = Sig('in', 'in', 'in')
    ResetRotationModes = Sig('in')
    SetRotationModes = Sig('in', 'in', 'in')
    SetMotorTravelLimits = Sig('in', 'in', 'in')
    GetMotorTravelLimits = Sig('in', 'in', 'in')
    RequestDigitalOutputs = Sig('in')
    GetDigitalOutputs = Sig('in')
    SetDigitalOutputs = Sig('in', 'in')
    GetRealValueFromDeviceUnit = Sig('in', 'in', 'in', 'in')
    GetDeviceUnitFromRealValue = Sig('in', 'in', 'in', 'in')

# similarly, a TLI_KSG class can be defined for TLI Strain gauges



############## This should be the end of the Level 2 Wrapper ##################
###############################################################################
