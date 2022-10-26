#
# @file iface_netcomms.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief The interface side of the GUI/Interface <==> Middleware network communications handling layer. Enables the GUI/Interface to be substituted for any other interface assuming this protocol is used.
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

# MMC communication is such that it is always the iface initiating contact with the middleware.
# Don't-Speak-Unless-Spoken-To Architecture

class IfaceNetComm:
    TX_PORT = 52042
    RX_PORT = 52043

    ID_IFACE = 0x1FACE
    ID_MIDW = 0xFACADE

    def __init__(self, address: str = 'localhost', tx_port: int = TX_PORT, rx_port: int = RX_PORT):
        self._connection_valid = False

        self.address = address
        self.tx_port = tx_port
        self.rx_port = rx_port

        self._data_dumm = None
        self._data_dumm_fresh = False
        self._data_home = None
        self._data_home_fresh = False 
        self._data_posn = None
        self._data_posn_fresh = False
        self._data_homg = None
        self._data_homg_fresh = False
        self._data_movg = None
        self._data_movg_fresh = False
        self._data_move = None
        self._data_move_fresh = False
        self._data_port = None
        self._data_port_fresh = False

        self._done = False

        pal = (self.address, self.rx_port)
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.skt.bind(pal)
        # self.skt.setblocking(False)
        self.skt.settimeout(0.1)

        self.rx_tid = threading.Thread(target=self._receiver)
        self.rx_tid.start()

        while self._connection_valid == False:
            self.transmit('INIT IFACE')
            print("Waiting for a response from the middleware...")
            time.sleep(0.25)

    def __del__(self):
        self._done = True

        self.rx_tid.join()
        print('Receiver thread terminated.')

    def check_connection(self):
        self._connection_valid = False
        while self._connection_valid == False:
            self.transmit('INIT IFACE')
            time.sleep(0.25)

    def _receiver(self):
        while self._done == False:
            try:
                msg, addr = self.skt.recvfrom(4096)
            except socket.error as e:
                continue
            print(msg.decode('utf-8'))
            msg_str = msg.decode('utf-8')

            if (msg_str[0:4] == 'DUMM'):
                self._data_dumm_fresh = True
                if msg_str[5:9] == 'TRUE':
                    self._data_dumm = True
                else:
                    self._data_dumm = False

            elif msg_str[0:4] == 'HOME':
                self._data_home_fresh = True
                self._data_home = msg_str[5:9]
            
            elif msg_str[0:4] == 'POSN':
                self._data_posn_fresh = True
                self._data_posn = msg_str[5:9]
            
            elif msg_str[0:4] == 'HOMG':
                self._data_homg_fresh = True
                if msg_str[5:9] == 'TRUE':
                    self._data_homg = True
                else:
                    self._data_homg = False
            
            elif msg_str[0:4] == 'MOVG':
                self._data_movg_fresh = True
                if msg_str[5:9] == 'TRUE':
                    self._data_movg = True
                else:
                    self._data_movg = False
            
            elif msg_str[0:4] == 'MOVE':
                self._data_move_fresh = True
                self._data_move = msg_str[5:9]

            elif msg_str[0:4] == 'PORT':
                self._data_port_fresh = True
                self._data_port = msg_str[5:]

            elif (msg_str == 'INIT MIDW'):
                self._connection_valid = True
            
            else:
                print("ERROR: Received unknown packet type.")
    
    def transmit(self, msg: str):
        self.skt.sendto(msg.encode('utf-8'), (self.address, self.tx_port))

    def get_data(self, data: str)->int:
        if data == 'is_dummy':
            while self._data_dumm_fresh == False:
                time.sleep(0.1)
            return self._data_dumm
            
        elif data == 'home':
            while self._data_home_fresh == False:
                time.sleep(0.1)
            return self._data_home

        elif data == 'get_position':
            while self._data_posn_fresh == False:
                time.sleep(0.1)
            return self._data_posn

        elif data == 'is_homing':
            while self._data_homg_fresh == False:
                time.sleep(0.1)
            return self._data_homg

        elif data == 'is_moving':
            while self._data_movg_fresh == False:
                time.sleep(0.1)
            return self._data_movg

        elif data == 'move_to':
            while self._data_move_fresh == False:
                time.sleep(0.1)
            return self._data_move

        elif data == 'find_all_ports':
            while self._data_port_fresh == False:
                time.sleep(0.1)
            return self._data_port
