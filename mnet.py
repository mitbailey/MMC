#
# @file mnet.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief Universal MMC network communications protocol handler.
# @version See Git tags for version information.
# @date 2022.10.31
# 
# @copyright Copyright (c) 2022
# 
#

import socket
import random
import zlib
import queue
import threading
import time

class MNet:
    MAX_RECV_SIZE = 2048
    SOCKET_TIMEOUT = 1
    MAX_LISTENEES = 5

    def __init__(self, ip: str, tx_port: int, rx_port: int):
        self.done = False
        self.peers_list = []

        self._rx_queue = [] # queue.Queue(maxsize=256)
        self._rx_queue_busy = False

        self.ID: bytearray = random.randint(0, 100000000).to_bytes(4, 'big')
        self.IP: str = ip
        self.PORT: int = tx_port

        self.tcp_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_sock.bind((self.IP, rx_port))
        self.tcp_sock.listen(MNet.MAX_LISTENEES)
        self.tcp_sock.settimeout(MNet.SOCKET_TIMEOUT)

        self.rx_tid = threading.Thread(self._receive)
        self.rx_tid.start()

    def packet(self, data: bytearray):
        packet_id: bytearray = zlib.crc32(time.time_ns).to_bytes(4, 'big')
        checksum: bytearray =  zlib.crc32(data).to_bytes(4, 'big')

        packet: bytearray = bytearray(
            self.ID +   # 4 bytes
            packet_id + # 4 bytes
            checksum +  # 4 bytes
            data +      # Unknown
            b'AAAA'     # 4 bytes
        )

        return packet, packet_id, checksum

    def _extract(self, packet):
        if (len(packet) < 16) or (packet[-5:] != b'AAAA'):
            return False, None, None, None, None

        _peerid = packet[0:4]
        _pktid = packet[4:8]
        _cs = packet[8:12]
        _data = packet[12:-5]

        if (_cs != zlib.crc32(_data).to_bytes(4, 'big')) or (_peerid not in self.peers_list):
            return False, None, None, None, None

        return True, _peerid, _pktid, _cs, _data

    def transmit(self, packet):
        # sndpkt = self._packet(data)
        self.tcp_sock.send(packet)

    def _receive(self):
        while not self.done:
            try:
                rcvpkt = self.tcp_sock.recv(MNet.MAX_RECV_SIZE)
            except socket.timeout:
                continue

            valid, _peerid, _pktid, _cs, _data = self._extract(rcvpkt)
            if valid:
                self._rx_queue.append((_peerid, _pktid, _cs, _data))  

    # def _pop_queue(self, index: int = 0):
        # self._rx_queue_busy = True

    # Removes messages from the queue until it finds what its looking for.
    def get(self, peerid: bytearray = None, pktid: bytearray = None, cs: bytearray = None):
        # self._rx_queue_busy = True
        # self._rx_queue_busy = False
        if peerid is None and pktid is None and cs is None:
            return self._rx_queue.pop(0)

        for i, pkt in self._rx_queue:
            if peerid is None and pktid is None and cs is not None:
                if pkt[2] == cs:
                    retval = self._rx_queue.pop(i)
                    self._rx_queue[0:i] = []
                    return retval
            
            elif peerid is None and pktid is not None and cs is None:
                if pkt[1] == pktid:
                    retval = self._rx_queue.pop(i)
                    self._rx_queue[0:i] = []
                    return retval
            
            elif peerid is None and pktid is not None and cs is not None:
                if pkt[1] == pktid and pkt[2] == cs:
                    retval = self._rx_queue.pop(i)
                    self._rx_queue[0:i] = []
                    return retval
            
            elif peerid is not None and pktid is None and cs is not None:
                if pkt[0] == peerid and pkt[2] == cs:
                    retval = self._rx_queue.pop(i)
                    self._rx_queue[0:i] = []
                    return retval
            
            elif peerid is not None and pktid is not None and cs is None:
                if pkt[0] == peerid and pkt[1] == pktid:
                    retval = self._rx_queue.pop(i)
                    self._rx_queue[0:i] = []
                    return retval
            
            elif peerid is not None and pktid is not None and cs is not None:
                if pkt[0] == peerid and pkt[1] == pktid and pkt[2] == cs:
                    retval = self._rx_queue.pop(i)
                    self._rx_queue[0:i] = []
                    return retval

        return None
                
