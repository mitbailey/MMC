#
# @file net.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief A simple test-enabling prototype for the MMC GUI/Interface <==> Middleware network communications handling layer.
# @version See Git tags for version information.
# @date 2022.10.25
# 
# @copyright Copyright (c) 2022
# 
#

import socket
import threading
import signal
import time
import sys

# Handles when the user presses ^C.
def sighandler(signal, x):
    print("KeyboardInterrupt\n^C")

    # This will signal the main thread to move from busy-waiting to waiting on join().
    global done 
    done = True

class UDPNet:
    def __init__(self):
        self.done = False
        self.address = 'localhost'

        self.tx_port: int = 52000 + int(input('TX on 52000 + '))
        print(self.tx_port)

        self.rx_port: int = 52000 + int(input('RX on 52000 + '))
        print(self.rx_port)
        print()

        pal = (self.address, self.rx_port)
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.skt.bind(pal)
        self.skt.setblocking(False)
        # self.skt.settimeout(1)

        self.tx_tid = threading.Thread(target=self.transmitter)
        self.rx_tid = threading.Thread(target=self.receiver)

        self.tx_tid.start()
        self.rx_tid.start()

    def __del__(self):
        self.done = True

        self.tx_tid.join()
        print('Transmitter thread terminated.')
        self.rx_tid.join()
        print('Receiver thread terminated.')

    def transmitter(self):
        while self.done == False:
            try:
                msg = input('')
            except Exception:
                self.done = True
            if msg == 'POSN':
                val = 4292
                msg = msg + ' ' + str(val)
            self.skt.sendto(msg.encode('utf-8'), (self.address, self.tx_port))

    def receiver(self):
        while self.done == False:
            try:
                msg, addr = self.skt.recvfrom(4096)
            except socket.error as e:
                # print(e)
                continue
            print(msg.decode('utf-8'))
            msg_str = msg.decode('utf-8')
            if msg_str[0:4] == 'POSN':
                print("Got POSN command with value:", msg_str[5:9])

#////////////////////////////#

class TCPNet:
    def __init__(self):
        self.done = False
        self.address = 'localhost'

        self.tx_port: int = 52000 + int(input('TX on 52000 + '))
        print(self.tx_port)

        self.rx_port: int = 52000 + int(input('RX on 52000 + '))
        print(self.rx_port)
        print()

        self.skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.skt.setblocking(False)
        # self.skt.settimeout(1)

        self.tx_tid = threading.Thread(target=self.transmitter)
        self.rx_tid = threading.Thread(target=self.receiver)

        self.tx_tid.start()
        self.rx_tid.start()

    def __del__(self):
        self.done = True

        self.tx_tid.join()
        print('Transmitter thread terminated.')
        self.rx_tid.join()
        print('Receiver thread terminated.')

    def transmitter(self):
        while self.done == False:
            try:
                self.skt.connect((self.address, self.tx_port))
            except Exception:
                time.sleep(1)
                continue
            break
        while self.done == False:
            try:
                msg = input('')
            except Exception:
                self.done = True
            self.skt.sendto(msg.encode('utf-8'), (self.address, self.tx_port))

    def receiver(self):
        self.skt.bind((self.address, self.rx_port))
        self.skt.listen(1)
        print('Accepting...')
        conn, addr = self.skt.accept()
        print('Accepted.')

        while self.done == False:
            try:
                msg, addr = self.skt.recvfrom(4096)
            except socket.error as e:
                # print(e)
                continue
            print(msg.decode('utf-8'))

if __name__ == '__main__':
    global done
    done = False

    # Register our ^C callback.
    signal.signal(signal.SIGINT, sighandler)
    
    nethandler = UDPNet()
    # nethandler = TCPNet()

    while not done:
        time.sleep(1)