from utilities import safe_serial
from utilities import log

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

comport = input('Port:')
log.register()
s = Initialize_Serial(comport)
Initialize_747(s)