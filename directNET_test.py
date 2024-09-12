# A minimum verifiable directNET test / example. Will be transitioned into a library for the 747 driver and moved to.utilities.

import time
# import directnet
from utilities import ports_finder
from utilities import safe_serial
from threading import Lock
# from utilities import log

# from .stagedevice import StageDevice

import serial
import six
# from directnet.common import ControlCodes
from codecs import encode, decode

memory_map = {
    'V': 1,
}

class Operation:
    READ = 0
    WRITE = 1

class ControlCodes:
    ENQ = b'\x05'  # Enquiry - initiate request
    ACK = b'\x06'  # Acknowledge - the communication was received without error
    NAK = b'\x15'  # Negative Acknowledge - there was a problem with the communication
    SOH = b'\x01'  # Start of Header - beginning of header
    ETB = b'\x17'  # End of Transmission Block - end of intermediate block
    STX = b'\x02'  # Start of Text - beginning of data block
    ETX = b'\x03'  # End of Text - End of last data block
    EOT = b'\x04'  # End of Transmission - the request is complete.

class DNClient(object):
    """
    Client for accessing serial port using DirectNET protocol

    @type serial: serial.Serial
    """

    ENQUIRY_ID = b'N'

    # This is where we set up RS232 / port communications.
    # 1 is the default client_id and its also the client_id of the 747...
    def __init__(self, port: serial.Serial, client_id: int = 1):
        self.s = safe_serial.SafeSerial(port, 9600, timeout=1)
        # self.serial = serial.serial_for_url(port, timeout=1, parity=serial.PARITY_ODD)
        self.client_id = client_id

    def test_connection(self):
        self.enquiry()

    def disconnect(self):
        self.s.close()

    def enquiry(self):
        self.s.write(self.ENQUIRY_ID + chr(0x20 + self.client_id).encode() + ControlCodes.ENQ)
        ack = self.s.read(size=3)
        assert ack == self.ENQUIRY_ID + chr(0x20 + self.client_id).encode() + ControlCodes.ACK, "ACK not received. Instead got: "+repr(ack)

    # Build a header.
    def get_request_header(self, oper: Operation, address, size):
        # Header
        header = ControlCodes.SOH

        # Client ID
        header += self._to_hex(self.client_id, 2)

        # Operation Read/Write 0/8
        header += self._to_hex(0 if (oper == Operation.READ) else 8, 1)

        # Data type
        memory_type = address[0]
        header += self._to_hex(memory_map[memory_type], 1)

        # Address
        address = address[1:]
        # Looks like the address is expected in octal.
        header += self._to_hex(int(address, base=8)+1, 4)

        # No of blocks, bytes in last block
        header += self._to_hex(size / 256, 2)
        header += self._to_hex(size % 256, 2)

        # master id = 0
        header += self._to_hex(0, 2)

        header += ControlCodes.ETB

        # Checksum
        header += self._calc_csum(header[1:15])

        return header

    # Builds a header, sends it, and then reads & returns the response.
    def read_value(self, address, size):
        self.enquiry()

        header = self.get_request_header(read=Operation.READ, address=address, size=size)
        self.s.write(header)

        self._read_ack()

        data = self._parse_data(size)

        self._write_ack()

        self._end_transaction()

        return data
    
    # UNVERIFIED
    def write_value(self, address, size):
        # TODO: Needs a place to put the payload...
        pass

    # Shorthand for read_value where we are looking for an integer.
    def read_int(self, address):
        data = self.read_value(address, 2)
        return int(encode(data[::-1], 'hex'))

    def _read_ack(self):
        ack = self.s.read(1)
        assert ack == ControlCodes.ACK, repr(ack) + ' != ACK'

    def read_end_of_text(self):
        etx = self.s.read(1)
        assert etx == ControlCodes.ETX, repr(etx) + ' != ETX'

    def _write_ack(self):
        self.s.write(ControlCodes.ACK)

    def _end_transaction(self):
        eot = self.s.read(1)
        assert eot == ControlCodes.EOT, 'Not received EOT: '+repr(eot)
        self.s.write(ControlCodes.EOT)

    def _parse_data(self, size):
        data = self.s.read(1 + size + 2)  # STX + DATA + ETX + CSUM
        return data[1:size+1]

    def _calc_csum(self, data):
        csum = 0

        for item in data:
            csum ^= self._to_int(item)

        return self._to_bytes(csum)

    def _to_hex(self, number, size):
        hex_chars = hex(number)[2:].upper()
        return ('0' * (size - len(hex_chars))) + hex_chars

    def _to_int(self, value):
        if isinstance(value, int):
            return value
        return ord(value)

    def _to_bytes(self, value):
        if six.PY3:
            return bytes((value,))
        return chr(value)

# print("DirectNET Test")
# dn_client = DNClient('COM5')
# dn_client.test_connection()
# dn_client.disconnect()
# 76543210
class SubDevice:
    DEV_0 = 0x01
    DEV_1 = 0x02
    DEV_2 = 0x04
    DEV_3 = 0x08

class Address:
    INIT = '40602'
    MOTION = '40601'
    ERROR = '40600'
    INCREMENT = '40600'
    POS_0 = '2240'
    POS_1 = '2241'
    POS_2 = '2242'
    POS_3 = '2243'
    DEST_0 = '2250'
    DEST_1 = '2251'
    DEST_2 = '2252'
    DEST_3 = '2253'

class Size:
    INIT = 1
    MOTION = 4
    ERROR = 1
    INCREMENT = 1
    POS_0 = 1
    POS_1 = 1
    POS_2 = 1
    POS_3 = 1
    DEST_0 = 1
    DEST_1 = 1
    DEST_2 = 1
    DEST_3 = 1

# NOTE: Everything in 747-land is in increments of 2 bytes
# aka V-Memory Words 
class Test747:
    def __init__(self, port: serial.Serial):
        self.dn = DNClient(port)
        self.dn.test_connection()

    # Functions for internal use.
    def _subdevice_init(self, dev):
        pass

    def _write_increment_position(self, dev):
        pass

    def _write_destination(self):
        pass

    def _read_init_flags(self):
        devis = self.dn.read_value(Address.INIT, Size.INIT)

        dev0 = devis & SubDevice.DEV_0
        dev1 = devis & SubDevice.DEV_1
        dev2 = devis & SubDevice.DEV_2
        dev3 = devis & SubDevice.DEV_3

        print('Initialization statuses:')
        print('dev0: %d, dev1: %d, dev2: %d, dev3: %d'%(dev0, dev1, dev2, dev3))

    def _read_error_flag(self):
        error = self.dn.read_value(Address.ERROR, Size.ERROR)

        print('Error status:')
        print('error: %d'%(error))

    def _read_motion_flags(self):
        motion = self.dn.read_value(Address.MOTION, Size.MOTION)

        dev_any = motion & 0x10000 # 0b0001_0000_0000_0000_0000
        dev_0 = motion & 0x20000 # 0b0010_0000_0000_0000_0000
        dev_1 = motion & 0x40000 # 0b0100_0000_0000_0000_0000
        dev_2 = motion & 0x80000 # 0b1000_0000_0000_0000_0000
        dev_3 = motion & 0x100000 # 0b1_0000_0000_0000_0000_0000

        print('Motion statuses:')
        print('dev_any: %d, dev_0: %d, dev_1: %d, dev_2: %d, dev_3: %d'%(dev_any, dev_0, dev_1, dev_2, dev_3))

    def _read_positions(self):
        pos_0 = self.dn.read_value(Address.POS_0, Size.POS_0)
        pos_1 = self.dn.read_value(Address.POS_1, Size.POS_1)
        pos_2 = self.dn.read_value(Address.POS_2, Size.POS_2)
        pos_3 = self.dn.read_value(Address.POS_3, Size.POS_3)

        print('Positions:')
        print('pos_0: %d, pos_1: %d, pos_2: %d, pos_3: %d'%(pos_0, pos_1, pos_2, pos_3))

    
