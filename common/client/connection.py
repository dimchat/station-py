# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# ==============================================================================

"""
    Socket Connection
    ~~~~~~~~~~~~~~~~~

    Connection for DIM Station and Robot Client
"""

import socket
import time
from abc import ABCMeta, abstractmethod
from threading import Thread

from dimp import Station, ITransceiverDelegate, ICompletionHandler
from dkd import InstantMessage


class IConnectionDelegate(metaclass=ABCMeta):

    @abstractmethod
    def receive_package(self, data: bytes):
        """ Receive data package

        :param data: data package
        :return:
        """
        pass


class Connection(ITransceiverDelegate):

    # boundary for packages
    BOUNDARY = b'\n'

    def __init__(self):
        super().__init__()
        self.delegate: IConnectionDelegate = None
        # current station
        self.station: Station = None
        self.connected = False
        # socket
        self.sock = None
        self.thread_receive = None
        self.thread_heartbeat = None
        self.last_time: int = 0

    def __del__(self):
        self.close()

    def close(self):
        # stop thread
        self.connected = False
        if self.thread_receive:
            self.thread_receive = None
        # disconnect the socket
        if self.sock:
            self.sock.close()

    def connect(self, station: Station):
        if self.sock:
            self.sock.close()
        # connect to new socket (host:port)
        self.station = station
        address = (station.host, station.port)
        self.sock = socket.socket()
        self.sock.connect(address)
        # start threads
        self.connected = True
        self.last_time = int(time.time())
        if self.thread_receive is None:
            self.thread_receive = Thread(target=receive_handler, args=(self,))
            self.thread_receive.start()
        if self.thread_heartbeat is None:
            self.thread_heartbeat = Thread(target=heartbeat_handler, args=(self,))
            self.thread_heartbeat.start()

    def send(self, data: bytes) -> IOError:
        self.last_time = int(time.time())
        try:
            self.sock.sendall(data)
        except IOError as error:
            # reconnect
            self.connect(station=self.station)
            # try again
            try:
                self.sock.sendall(data)
            except IOError as error:
                # failed
                return error

    def receive(self, pack: bytes):
        self.last_time = int(time.time())
        self.delegate.receive_package(data=pack)

    #
    #   ITransceiverDelegate
    #
    def send_package(self, data: bytes, handler: ICompletionHandler) -> bool:
        """ Send out a data package onto network """
        # pack
        pack = data + self.BOUNDARY
        # send
        error = self.send(data=pack)
        if handler is not None:
            if error is None:
                handler.success()
            else:
                handler.failed(error=error)
        return True

    def upload_data(self, data: bytes, msg: InstantMessage) -> str:
        """ Upload encrypted data to CDN """
        pass

    def download_data(self, url: str, msg: InstantMessage) -> bytes:
        """ Download encrypted data from CDN, and decrypt it when finished """
        pass


def receive_handler(conn: Connection):
    data = b''
    while conn.connected:
        # read all data
        try:
            data += conn.sock.recv(1024)
        except OSError:
            break
        # split package(s)
        pos = data.find(conn.BOUNDARY)
        while pos != -1:
            pack = data[:pos]
            conn.receive(pack=pack)
            # next package
            pos += len(conn.BOUNDARY)
            data = data[pos:]
            pos = data.find(conn.BOUNDARY)


def heartbeat_handler(conn: Connection):
    while conn.connected:
        time.sleep(5)
        now = int(time.time())
        delta = now - conn.last_time
        if delta > 300:
            # heartbeat after 5 minutes
            conn.send(data=b'\n')
