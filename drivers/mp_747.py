#
# @file mp_747.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief 
# @version See Git tags for version information.
# @date 2023.08.23
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
from utilities import ports_finder
from utilities import safe_serial
from threading import Lock
from utilities import log

from .stagedevice import StageDevice

class MP_747(StageDevice):
    WR_DLY = 0.05

    ENQ = bytearray(b'N!\x05')
    ACK = bytearray(b'N!\x06')
    NACK = bytearray(b'N!\x15')
    EOT = bytearray(b'\x15')
    STX = bytearray(b'\x02')
    ETX = bytearray(b'\x03')

    def backend(self)->str:
        return 'MP_747'

    def __init__(self, port):
        self.s_name = 'MP747'
        self.l_name = 'McPherson 747'
        self._is_homing = False
        self._moving = False
        self.moving_poll_mutex = Lock()
        self.stop_queued = 0
        self._position = 0

        log.info('Attempting to connect to McPherson Model 747 Device Controller on port %s.'%(port))

        # Check if we were given a port.
        if port is None:
            log.error('Port is none type.')
            raise RuntimeError('Port is nonetype.')
        
        # Check if the port is available.
        ser_ports = ports_finder.find_serial_ports()
        if port not in ser_ports:
            log.error('Port not valid. Is another program using the port?')
            raise RuntimeError('Port not valid. Is another program using the port?')
        
        # Get a SafeSerial connection on the port and begin communication.
        self.s = safe_serial.SafeSerial(port, 9600, timeout=0.5)
        
        # TODO: Begin communication a la 789, and get rid of these weird functions.

        # A short communication to determine if the 747 is alive / exists.
        if not self._comms_detect():
            log.error('Could not detect MP747 on port %s.'%(port))
            raise RuntimeError('Could not detect MP747 on port %s.'%(port))
        
        # Initialize the 747.
        if not self._comms_init(True, False, False, False):
            log.error('Could not initialize MP747 on port %s.'%(port))
            raise RuntimeError('Could not initialize MP747 on port %s.'%(port))

        # May not be desired / applicable???
        self.home()

    # The _comms functions help hide some of the complexity of the 747's communication protocol.
    def _comms_detect(self)->bool:
        """ Detects whether we are able to talk to an MP747.

        Returns:
            bool: False on failure, True on success.
        """

        TO_RETRIES = 5
        to_retries = 0
        while (to_retries < TO_RETRIES):
            self.s.write(MP_747.ENQ)
            msg = self.s.read(128)

            if msg != MP_747.ACK:
                if MP_747.EOT in msg:
                    # The 747 timed-out internally.
                    log.warn('747 timed-out internally.')
                    to_retries += 1
                    continue
                return False

            self.s.write(MP_747.EOT)
            msg = self.s.read(128)

            self.s.write(MP_747.EOT)
            break

        return True

    def _comms_init(self, dev_1: bool, dev_2: bool, dev_3: bool, dev_4: bool)->bool:
        """ Initializes the 747.

        Args:
            dev_maske (int): Four-bit binary mask, 1 = init, 0 = ignore. Bits 0-3 correspond to devices 1-4.
        
        Returns:
            bool: False on failure, True on success.
        """

        # Build the 0b0000 device initialization bitmask sequence from the four booleans.
        dev_mask = 0
        if dev_1:
            dev_mask |= 1
        if dev_2:
            dev_mask |= 2
        if dev_3:
            dev_mask |= 4
        if dev_4:
            dev_mask |= 8

        if dev_mask < 0 or dev_mask > 15:
            log.error('Invalid device mask.')
            raise RuntimeError('Invalid device mask.')
        
        # Convert the bitmask to a string in hex format. `hex()` gives us '0x', so [2:] skips that. This gives us the data we want to write in this scenario.
        dev_mask_str = hex(dev_mask)[2:]
        log.debug('Bitmask as a hex string:', dev_mask_str)

        self.s.write(MP_747.ENQ) # Enquiry
        msg = self.s.read(128) # Expected: ACK

        if msg != MP_747.ACK:
            return False
        
        header = self._header('w', '4181')
        if header is None:
            return False
        
        self.s.write(header) # Header
        msg = self.s.read(128) # Expected: ACK

        # UNKNOWN WHAT WILL BE RETURNED HERE. CHECK BEFORE PROCEEDING.
        print(msg)

        data = self._data(dev_mask_str) # Generates a 747-friendly data block.
        if data is None:
            return False
        self.s.write(data) # Writes the data block.
        msg = self.s.read(128) # Expected: ACK

        # UNKNOWN WHAT WILL BE RETURNED HERE. CHECK BEFORE PROCEEDING.
        print(msg)

        # Supposedly after that last ACK, we are supposed to send more data (??) and then another ACK, etc.
        # Here I just assume one set of data is enough and finish.

        self.s.write(MP_747.EOT)

        return True

        # Header ->
        # <- ACK
        # <- DATA
        # ACK ->
        # <- DATA
        # ACK ->
        # <- EOT
        # EOT ->


    def _comms_query_motion(self, device: int):
        """ Queries the MP747 for its motion status.

        Args:
            device (int): 0 for any motion, 1 - 4 for a specific device's motion.
        """

        pass

    def _comms_query_error(self):
        """ Queries the MP747 for its error status.
        """

        pass

    def _comms_query_position(self, device: int):
        """ Queries the MP747 for the position of a device.

        Args:
            device (int): 1 - 4 for a specific device.
        """

        pass

    def _comms_set_destination(self, device: int, position: int):
        """ Sets the destination of a device.

        Args:
            device (int): 1 - 4 for a specific device.
            position (int): The position to set the device to.
        """

        pass
    
    def _lrc(self, data: bytearray)->bytearray or None:
        pass

    def _data(self, data: str)->bytearray or None:
        """ Builds a 747 data block.

        Args:
            data (str): The data to be written.

        Raises:
            RuntimeError: _description_

        Returns:
            _type_: _description_
        """

        if type(data) is not str:
            log.error('The data parameter must be a string.')
            raise RuntimeError('The data parameter must be a string.')

        if len(data) != 4:
            log.error('The data parameter must be four characters long.')
            raise RuntimeError('The data parameter must be four characters long.')

        data_block = bytearray()
        data_block.append(MP_747.STX)
        data_block.append(data[2])
        data_block.append(data[3])
        data_block.append(data[0])
        data_block.append(data[1])
        data_block.append(MP_747.ETX)
        lrc = self._lrc(data_block[1:5])
        data_block.append(lrc[0]) # LRC byte #1
        data_block.append(lrc[1]) # LRC byte #2

        return data_block

    def _header(self, rw: str, str_data_addr: str)->bytearray or None:
        """ Builds a 747 header.

        Args:
            rw (str): 'r' for read, 'w' for write.
            str_data_addr (str): The four-character ASCII address to access (e.g. '04A1').

        Raises:
            RuntimeError: _description_

        Returns:
            _type_: _description_
        """

        if type(str_data_addr) is not str:
            log.error('The str_data_addr parameter must be a string.')
            raise RuntimeError('The str_data_addr parameter must be a string.')

        if len(str_data_addr) != 4:
            log.error('The str_data_addr parameter must be four characters long.')
            raise RuntimeError('The str_data_addr parameter must be four characters long.')

        header = bytearray()
        header.append(0x1) # SOH
        header.append(0x30) # Controller address
        header.append(0x31) # Controller address

        # Operation read or write.
        if rw == 'r':
            header.append(0x30)
        elif rw == 'w':
            header.append(0x38)
        else:
            log.error('Invalid read/write value.')
            raise RuntimeError('Invalid read/write value.')
        
        header.append(0x31) # Data type (V Memory)
        
        # Append mem addr MSB
        header.append(0x30)
        header.append(0x30)
        # Append mem addr LSB
        header.append(0x30)
        header.append(0x30)
        
        # For remote control of the 747, the full data blocks should never need to be used.
        header.append(0x30) # Complete data blocks (none)
        header.append(0x30) # Complete data blocks (none)

        header.append(0x30) # Partial data block (0) bytes
        header.append(0x34) # Partial data block (4) bytes

        header.append(0x30) # Host computer address
        header.append(0x31) # Host computer address
        header.append(0x17) # ETB

        # Append LRC checksum
        log.warn('LRC checksum not yet implemented.')
        header.append(0x00) # LRC CS
        header.append(0x00) # LRC CS

        return header

    def set_stage(self, stage):
        pass

    def get_stage(self):
        return None

    def home(self)->bool:
        """_summary_

        Returns:
            bool: _description_
        """

        pass

    def get_position(self):
        """_summary_
        """

        pass

    def stop(self):
        """_summary_
        """

        pass

    def is_moving(self):
        """_summary_
        """

        pass

    def is_homing(self):
        """_summary_
        """

        pass

    def move_to(self, position: int, backlash: int):
        pass

    def move_relative(self, steps: int):
        pass

    def short_name(self):
        pass

    def long_name(self):
        pass

    def open(self):
        pass

    def close(self):
        self.s.close()

""" 
747 Communication Protocol
==========================
    - After 800 milliseconds of no response, the communication should be considered timed-out.
    - If the master does not reply within 800 milliseconds, the 747 will time-out and send an <EOT>.

Enquiry [ENQ]
-------
    Three-byte message. 

    0: is 0x4e ('N' for "Normal").
    1: is the offset address, 0x1 by default, plus 0x20. resulting in 0x21.
    2: is 0x5 <ENQ>. 

    Typical: 0x4e 0x21 0x4e

N/Acknowledgement
---------------
    Three-byte message.

    0: is 0x4e ('N' for "Normal").
    1: is the offset address, 0x1 by default, plus 0x20. resulting in 0x21.
    2: is 0x6 <ACK> for ACK, 0x15 <NAK> for NACK.

    Typical ACK:  0x4e 0x21 0x6
    Typical NACK: 0x4e 0x21 0x15

Header
------
    18-byte message.

    Bytes       Write       Read        Description
    0           0x1         0x1         Start of header <SOH>.
    1, 2        0x30 0x31   0x30 0x21   Controller address (default).
    3           0x38        0x30        Operation write or read.
    4           0x31        0x31        Data type (V Memory).
    5, 6        0x34 0x31   0x31 0x34   Starting memory address (MSB).  
    7, 8        0x38 0x31   0x41 0x31   Starting memory address (LSB).
    9, 10       0x30 0x30   0x30 0x30   Complete data blocks (none).
    11, 12      0x30 0x34   0x30 0x34   Partial data block (four bytes).
    13, 14      0x30 0x31   0x30 0x31   Host computer address.
    15          0x17        0x17        End of transmission <ETB>.
    16, 17                              Checksum (LRC).

    The Hex ASCII reference addresses needed for the message header are found by converting the octal address to hex
    and adding one. This value is then converted, character by character, to a literal ASCII  value.
    
    Example (0xNNN = hex, 0NNN = octal, NNN = decimal):
        02240 == 0x04A0
        0x04A0 + 1 = 0x04A1
        0x04A1 --> '0', '4', 'A', '1' --> 0x30 0x34 0x41 0x31
    
    This example corresponds to bytes 5, 6 and 7, 8 in the header shown above.

    Addresses
    ---------
        Initialization Flags
        "4183" bits 0 - 3.
            Read-only.
            Bits 0 - 3 correspond to devices 1 - 4. 
            1 = not initialized, 0 = ready. 
            Initialize device using 'Increment Position Bits'.

        In-Motion Flags
        "4182" bits 16 - 20.
            Read-only.
            Bit 16 is 1 if any device is in motion.
            Bits 17 - 20 correspond to devices 1 - 4.
            1 = in motion, 0 = not in motion.

        Error Flag
        "4181" bit 8.
            Read-only.
            1 = error, 0 = no error.

        Increment Position Bits
        "4181" bits 0 - 3.
            Read / write.
            Bits 0 - 3 correspond to devices 1 - 4.
            Set the relevant bit to '1' to initialize the device.
            Move the device forward one position.

        Current Positions
        "04A1" device 1.
        "04A2" device 2.
        "04A3" device 3.
        "04A4" device 4.
            Read-only.

        Destinations
        "04A9" device 1.
        "04AA" device 2.
        "04AB" device 3.
        "04AC" device 4.
            Read / write.
            Write the position in to go directly there, as opposed to moving one step at a time using the Incrementer.

Data
----
    256-byte blocks plus final sub-256-byte block.

    0           0x2         Start of text <STX>.
    1           0x30        Data byte #3.
    2           0x31        Data byte #4.
    3           0x30        Data byte #1.
    4           0x30        Data byte #2.
    5           0x3         End of text <ETX>.
    6, 7        0x30 0x31   Checksum (LRC).



0x5         Initiate request.
0x6         ACK.
0x15        NAK.
0x1         Beginning of header.
0x17        Start of transmission block; end of immediate block.
0x2         Beginning of data block.
0x3         End of data block.
0x4         End of transmission.

==========================
READ REQUEST
Master              Slave
[ENQ]
                    [ACK]
[HDR]        
                    [ACK]
                    [DATA]
[ACK]
                    [DATA]
[ACK]
                    0x4 <EOT>
0x4 <EOT>

WRITE REQUEST
Master              Slave
[ENQ]
                    [ACK]
[HDR]        
                    [ACK]
                    
[DATA]
                    [ACK]
[DATA]
                    [ACK]
0x4 <EOT>
 """

def print_bytes(message: bytearray):
    """ Print a bytearray as a string of hex values. """
    print(" ".join("0x{:02x}".format(b) for b in message))

def int_to_bytes(value: int, length: int):
    """ Convert an integer to a bytearray of a given length. """
    return value.to_bytes(length, byteorder='big')

def bytes_to_int(message: bytearray):
    """ Convert a bytearray to an integer. """
    return int.from_bytes(message, byteorder='big')

def lrc(message: bytearray):
    """ Calculate the Longitudinal Redundancy Check (LRC) for a message. """

    checksum = 0
    for b in message:
        checksum ^= b
    return checksum

def Initialize_Serial(comport: str):
    """ Initialize the serial port. """
    
    # Using 0.8s timeout, as the manual suggests, results in the 747 cancelling comms due to it timing-out internally. 0.5s avoids this.
    return safe_serial.SafeSerial(comport, 9600, timeout=0.5)

def Initialize_747(s):
    """ Initialize the 747. """

    # Setup our bytearrays / commands.
    ENQ = bytearray(b'N!\x05')
    ACK = bytearray(b'N!\x06')
    NACK = bytearray(b'N!\x15')
    EOT = bytearray(b'\x15')

    # First let's just try a basic enquiry, reading the ACK, and then sending EOT.
    # This is just a basic test.
    s.write(ENQ)
    msg = s.read(128)

    s.write(EOT)
    msg = s.read(128)

    s.write(EOT)

if __name__ == "__main__":
    comport = input('Port:')
    log.register()
    
    # s = Initialize_Serial(comport)
    # Initialize_747(s)

    mp747 = MP_747(comport)
