#
# @file ports_finder.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Provides a layer of abstraction between the MMC GUI and the underlying hardware device drivers.
# @version See Git tags for version information.
# @date 2022.09.23
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

import sys
import glob
import serial
from drivers import tl_kst101 as tlkt
import serial.tools.list_ports

from time import perf_counter_ns

APT_START = None
APT_DEVICELIST = []

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
    global APT_START, APT_DEVICELIST
    if APT_START is None:
        APT_START = perf_counter_ns()
    else:
        now = perf_counter_ns()
        print("Time since last APT port search: %d ns %f ms"%(now - APT_START, (now - APT_START) * 1e-6))
        if (now - APT_START)*1e-9 < 0.25:
            return APT_DEVICELIST
        APT_START = now

    serials = tlkt.ThorlabsKST101.list_devices()

    devices = []
    for dev in serials:
        info = tlkt.ThorlabsKST101.get_device_info(dev)
        devices.append(f'{info["serial_no"]} {info["model_no"]} {info["fw_ver"]}')
    APT_DEVICELIST = devices
    return devices

def generate_virtual_ports(num):
    virt_dev_list = []
    for i in range(num):
        virt_dev_list.append('VIRTUAL_%d - For testing purposes.'%(i))
    return virt_dev_list

def find_all_ports(virtualize):
    try:
        if generate_virtual_ports:
            return find_com_ports() + find_apt_ports() + generate_virtual_ports(5)
        else:
            return find_com_ports() + find_apt_ports()
    except Exception as e:
        exit("Error finding ports: %s"%(e))