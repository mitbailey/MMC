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
        self.dummy_mode = True # All or nothin'
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
            print('MIDW RX:', msg.decode('utf-8'))
            msg_str = msg.decode('utf-8')
            keys = msg_str.split(' ')

            if (msg_str[0:4] == 'DUMM'):
                if self.dummy_mode:
                    self.transmit('DUMM TRUE')
                else:
                    self.transmit('DUMM FALS')

            elif msg_str[0:4] == 'HOME':
                self.motion_controller.home()
            
            elif msg_str[0:4] == 'POSN':
                retval = self.motion_controller.get_position()
                print('get_position()', retval)
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
                    self.transmit('MOVG TRUE')
                else:
                    self.transmit('MOVG FALS')
            
            elif msg_str[0:4] == 'MOVE':
                if keys[2] == 'NONBLOCKING':
                    self.motion_controller.move_to(int(keys[1]), False)
                elif keys[2] == 'BLOCKING':
                    self.motion_controller.move_to(int(keys[1]), True)
                else:
                    print("Unknown move command structure.")

                self.transmit('MOVE DONE')

            elif msg_str[0:4] == 'PORT':
                dev_list = ports_finder.find_all_ports()
                dev_list_str = ''
                for dev in dev_list:
                    dev_list_str += '%s\n'%(dev)
                self.transmit('PORT %s'%(dev_list_str))

            # Network and device initialization commands.
            elif keys[0] == 'INIT' and keys[1] == 'IFACE':
                self.transmit('INIT MIDW')

            elif keys[0] == 'INIT' and keys[1] == 'DEVS':
                if keys[2] == 'REAL':
                    self.dummy_mode = False
                elif keys[2] == 'DUMM':
                    self.dummy_mode = True
                else:
                    print("ERROR: keys[2] was '%s', not 'REAL' nor 'DUMM'."%(keys[2]))
                    # self.transmit('%s %s TRUE'%(keys[0], keys[1]))
                print('Dummy mode set to:', self.dummy_mode)

                dev_keys = msg_str[16:].split('\n')
                print('Split')
                print(msg_str[16:])
                print('into')
                for key in dev_keys:
                    print(key)

                mtnc_status = False
                dats_status = False
                clrw_status = False

                self.motion_controller = None
                self.data_sampler = None
                self.color_wheel = None

                try:
                    self.motion_controller = midw.MotionController(self.dummy_mode, dev_keys[0])
                except Exception as e:
                    print("Exception:", e)
                    self.motion_controller = None
                else:
                    mtnc_status = True

                try:
                    self.data_sampler = midw.DataSampler(self.dummy_mode, dev_keys[1])
                except Exception as e:
                    print("Exception:", e)
                    self.data_sampler = None
                else:
                    dats_status = True

                try:
                    self.color_wheel = midw.ColorWheel(self.dummy_mode, dev_keys[2])
                except Exception as e:
                    print("Exception:", e)
                    self.color_wheel = None
                else:
                    clrw_status = True

                if (self.motion_controller is not None) and (mtnc_status):
                    self.transmit('INIT MTNC TRUE')
                else:
                    self.transmit('INIT MTNC FALS')

                if (self.data_sampler is not None) and (dats_status):
                    self.transmit('INIT DATS TRUE')
                else:
                    self.transmit('INIT DATS FALS')
   
                if (self.color_wheel is not None) and (clrw_status):
                    self.transmit('INIT CLRW TRUE')
                else:
                    self.transmit('INIT CLRW FALS')

            elif keys[0] == 'SAMP':
                self.transmit('SAMP ' + str(self.data_sampler.sample_data()))

            elif keys[0] == 'MM_TO_IDX':
                self.transmit('MM_TO_IDX ' + str(self.motion_controller.mm_to_idx))

            else:
                print("ERROR: Received unknown packet type.")
    
    def transmit(self, msg: str):
        print('MIDW TX:', msg)
        self.skt.sendto(msg.encode('utf-8'), (self.address, self.tx_port))