# Test program for communication with the Picoammeter.

import serial

f = open("data.txt", 'w')

s = serial.Serial('COM3', 9600, timeout=1)
print('Communicating on port %s.'%(s.name))
# s.write(b'*IDN?\r')

s.write(b'*IDN?\r')
buf = s.read(128).decode('utf-8').rstrip()
print(buf)

if 'KEITHLEY INSTRUMENTS INC.,MODEL 6485' in buf:
    print("Keithley Model 6485 found.")
else:
    print("Keithley Model 6485 not found.")
    exit()

s.write(b'ARM:COUN 10\r')
buf = s.read(128).decode('utf-8').rstrip()
print(buf)
# exit()

s.write(b'CONF:CURR?\r')
buf = s.read(128).decode('utf-8').rstrip()
print(buf)

s.write(b'MEAS?\r')
buf = s.read(128).decode('utf-8').rstrip()
print(buf)


s.write(b'FETC?\r')
buf = s.read(128).decode('utf-8').rstrip()
print(buf)

# s.write(b'TRIG:COUN 10\r')
# buf = s.read(128).decode('utf-8').rstrip()
# print(buf)

print("\n\nDATA, TIMESTAMP, ERROR")

for i in range(10):
    s.write(b'READ?\r')
    buf = s.read(128).decode('utf-8').rstrip()
    print(buf)
    f.write(buf + '\n')

    spbuf = buf.split(',')
    if int(float(spbuf[2])):
        print("ERROR #%d", int(float(spbuf[2]))) 

f.close()
s.close()