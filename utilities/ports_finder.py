import sys
import glob
import serial
from drivers import _thorlabs_kst_advanced as tlkt
import serial.tools.list_ports

# Unknown if this works on Linux.
def find_com_ports():
    ports = serial.tools.list_ports.comports()

    dev_list = []
    for port, desc, hwid in sorted(ports):
        dev_list.append("%s %s %s"%(port, desc, hwid))
    return dev_list

def find_serial_ports():
    """ Lists serial port names

        :raises EnvironmentError:
            On unsupported or unknown platforms
        :returns:
            A list of the serial ports available on the system
    """
    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i + 1) for i in range(256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result

"""
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
"""
def find_apt_ports():
    serials = tlkt.Thorlabs.ListDevicesAny()

    devices = []
    for dev in serials:
        info = tlkt.Thorlabs.GetDeviceInfo(dev)
        devices.append(str(dev) + ' ' + info['description'])
    
    return devices

def find_all_ports():
    return find_com_ports() + find_apt_ports()