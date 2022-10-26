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

import middleware as midw
from utilities import ports_finder

# MMC communication is such that it is always the iface initiating contact with the middleware.
# Don't-Speak-Unless-Spoken-To Architecture

class MidwNetComm:
    TX_PORT = 52043
    RX_PORT = 52042

    ID_IFACE = 0x1FACE
    ID_MIDW = 0xFACADE

    def __init__(self, address: str = 'localhost', tx_port: int = TX_PORT, rx_port: int = RX_PORT):
        self._connection_valid = False

        self.address = address
        self.tx_port = tx_port
        self.rx_port = rx_port

        self.motion_controller: midw.MotionController = None
        self.data_sampler: midw.DataSampler = None
        self.color_wheel: midw.ColorWheel = None

        # self._data_dumm = None
        # self._data_dumm_fresh = False
        # self._data_home = None
        # self._data_home_fresh = False 
        # self._data_posn = None
        # self._data_posn_fresh = False
        # self._data_homg = None
        # self._data_homg_fresh = False
        # self._data_movg = None
        # self._data_movg_fresh = False
        # self._data_move = None
        # self._data_move_fresh = False
        # self._data_port = None
        # self._data_port_fresh = False

        self._done = False

        pal = (self.address, self.rx_port)
        self.skt = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.skt.bind(pal)
        # self.skt.setblocking(False)
        self.skt.settimeout(0.1)

        self.rx_tid = threading.Thread(target=self._receiver)
        self.rx_tid.start()

        # while self._connection_valid == False:
        #     self.transmit('INIT IFACE')
        #     print("Waiting for a response from the middleware...")
        #     time.sleep(0.25)

    def __del__(self):
        self._done = True

        self.rx_tid.join()
        print('Receiver thread terminated.')

    # def check_connection(self):
    #     self._connection_valid = False
    #     while self._connection_valid == False:
    #         self.transmit('INIT IFACE')
    #         time.sleep(0.25)

    def _receiver(self):
        while self._done == False:
            try:
                msg, addr = self.skt.recvfrom(4096)
            except socket.error as e:
                continue
            print(msg.decode('utf-8'))
            msg_str = msg.decode('utf-8')

            if (msg_str[0:4] == 'DUMM'):
                pass

            elif msg_str[0:4] == 'HOME':
                self.motion_controller.home()
            
            elif msg_str[0:4] == 'POSN':
                retval = self.motion_controller.get_position()
                self.transmit('POSN %s'%(str(retval)))
            
            elif msg_str[0:4] == 'HOMG':
                retval = self.motion_controller.is_homing()
                if retval:
                    self.transmit('HOMG TRUE')
                else:
                    self.transmit('HOMG FALS')
            
            elif msg_str[0:4] == 'MOVG':
                retval = self.motion_controller.is_moving()
                if retval:
                    self.transmit('HOMG TRUE')
                else:
                    self.transmit('HOMG FALS')
            
            elif msg_str[0:4] == 'MOVE':
                self.motion_controller.move_to(int(msg_str[5:]))

            elif msg_str[0:4] == 'PORT':
                dev_list = ports_finder.find_all_ports()
                dev_list_str = ''
                for dev in dev_list:
                    dev_list_str += '%s\n'%(dev)
                self.transmit('PORT %s'%(dev_list_str))

            elif msg_str[0:4] == 'INIT':
                keys = msg_str.split(' ')

                if keys[1] == 'IFACE':
                    self.transmit('INIT MIDW')

                elif keys[1] == 'MTNC': # MoTioN Controller
                    pass

                elif keys[1] == 'DATS': # DATa Sampler
                    pass

                elif keys[1] == 'CLRW': # CoLoR Wheel
                    pass

                else:
                    print("ERROR: Received unknown packet type.")

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
