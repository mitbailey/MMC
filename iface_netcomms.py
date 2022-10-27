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

from numpy import double

from PyQt5.QtCore import QThread

# MMC communication is such that it is always the iface initiating contact with the middleware.
# Don't-Speak-Unless-Spoken-To Architecture

class IfaceNetComm(QThread):
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
        self._data_posn = 0
        self._data_posn_fresh = False
        self._data_homg = None
        self._data_homg_fresh = False
        self._data_movg = None
        self._data_movg_fresh = False
        self._data_move = None
        self._data_move_fresh = False
        self._data_port = None
        self._data_port_fresh = False

        self._status_dats = False
        self._status_dats_fresh = False
        self._status_mtnc = False
        self._status_mtnc_fresh = False
        self._status_clrw = False
        self._status_clrw_fresh = False

        self._value_samp = ''
        self._value_samp_fresh = False
        self._value_idx = 0
        self._value_idx_fresh = False

        self._data_move_complete = False

        self._done = False

        pal = (self.address, self.rx_port)
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.skt.bind(pal)
        # self.skt.setblocking(False)
        self.skt.settimeout(0.1)

        self.rx_tid = threading.Thread(target=self._receiver)
        self.rx_tid.start()

        self.val_tid = threading.Thread(target=self._validate_connection)
        self.val_tid.start()

    def __del__(self):
        self._done = True

        self.rx_tid.join()
        print('Receiver thread terminated.')

    def _validate_connection(self):
        self._connection_valid = False
        while self._connection_valid == False and self._done == False:
            print("Waiting for a response from the middleware...")
            self.transmit('INIT IFACE')
            time.sleep(0.25)

    def online(self):
        return self._connection_valid

    # TODO: Make more intelligent.
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
            print('IFACE RX:', msg.decode('utf-8'))
            msg_str = msg.decode('utf-8')
            keys = msg_str.split(' ')

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

            # Network and device initialization commands.
            elif msg_str[0:4] == 'INIT':
                # keys = msg_str.split(' ')

                if keys[1] == 'MIDW':
                    self._connection_valid = True

                elif keys[1] == 'MTNC': # MoTioN Controller
                    self._status_mtnc_fresh = True
                    if keys[2] == 'TRUE':
                        self._status_mtnc = True
                    else:
                        self._status_mtnc = False

                elif keys[1] == 'DATS': # DATa Sampler
                    self._status_dats_fresh = True
                    if keys[2] == 'TRUE':
                        self._status_dats = True
                    else:
                        self._status_dats = False

                elif keys[1] == 'CLRW': # CoLoR Wheel
                    self._status_clrw_fresh = True
                    if keys[2] == 'TRUE':
                        self._status_clrw = True
                    else:
                        self._status_clrw = False

                else:
                    print("ERROR: Received unknown packet type.")

            elif keys[0] == 'SAMP':
                self._value_samp = msg_str[6:]
                self._value_samp_fresh = True

            elif keys[0] == 'MM_TO_IDX':
                self._value_idx = float(msg_str[10:])
                print(msg_str[10:])
                self._value_idx_fresh = True

            else:
                print("ERROR: Received unknown packet type.")
    
    def transmit(self, msg: str):
        print('IFACE TX:', msg)
        self.skt.sendto(msg.encode('utf-8'), (self.address, self.tx_port))

    def get_data(self, data: str, blocking: bool = False)->int:
        if data == 'is_dummy':
            while self._data_dumm_fresh == False and blocking:
                time.sleep(0.1)
            self._data_dumm_fresh == False
            return self._data_dumm
            
        elif data == 'home':
            while self._data_home_fresh == False and blocking:
                time.sleep(0.1)
            self._data_home_fresh == False
            return self._data_home

        elif data == 'get_position':
            while self._data_posn_fresh == False and blocking:
                time.sleep(0.1)
            self._data_posn_fresh == False
            return self._data_posn

        elif data == 'is_homing':
            while self._data_homg_fresh == False and blocking:
                time.sleep(0.1)
            self._data_homg_fresh == False
            return self._data_homg

        elif data == 'is_moving':
            while self._data_movg_fresh == False and blocking:
                time.sleep(0.1)
            self._data_movg_fresh == False
            return self._data_movg

        elif data == 'move_to':
            while self._data_move_fresh == False and blocking:
                time.sleep(0.1)
            self._data_move_fresh == False
            return self._data_move

        elif data == 'find_all_ports':
            if blocking:
                while self._data_port_fresh == False:
                    time.sleep(0.1)
                self._data_port_fresh == False
            if self._data_port_fresh:
                return self._data_port
            else:
                return ''

        elif data == 'move_complete':
            if blocking:
                while self._data_move_complete == False:
                    time.sleep(0.1)
            retval = self._data_move_complete
            self._data_move_fresh = False
            return retval

    def get_value(self, val: str, blocking: bool = True):
        if val == 'sample_data':
            wouldblock = not self._value_samp_fresh
            if blocking:
                while self._value_samp_fresh == False:
                    time.sleep(0.1)
            self._value_samp_fresh = False
            return self._value_samp, wouldblock

        elif val == 'mm_to_idx':
            wouldblock = not self._value_idx_fresh
            if blocking:
                while self._value_idx_fresh == False:
                    time.sleep(0.1)
            self._value_idx_fresh = False
            return self._value_idx, wouldblock

    def get_status(self, dev: str, blocking: bool = True):
        if dev == 'dats':
            wouldblock = not self._status_dats_fresh
            if blocking:
                while self._status_dats_fresh == False:
                    time.sleep(0.1)
            self._status_dats_fresh = False
            return self._status_dats, wouldblock
        elif dev == 'mtnc':
            wouldblock = not self._status_mtnc_fresh
            if blocking:
                while self._status_mtnc_fresh == False:
                    time.sleep(0.1)
            self._status_mtnc_fresh = False
            return self._status_mtnc, wouldblock
        elif dev == 'clrw':
            wouldblock = not self._status_clrw_fresh
            if blocking:
                while self._status_clrw_fresh == False:
                    time.sleep(0.1)
            self._status_clrw_fresh = False
            return self._status_clrw, wouldblock
        else:
            print("Unknown status request '%s'."%(dev))

