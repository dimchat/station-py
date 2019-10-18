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
from dimp import InstantMessage

from ..utils import Log


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
        self.__station: Station = None
        self.__connected = False
        # socket
        self.__sock = None
        self.__thread_receive = None
        self.__thread_heartbeat = None
        self.__last_time: int = 0

    def __del__(self):
        self.close()

    @property
    def connected(self) -> bool:
        return self.__connected

    @property
    def last_time(self) -> int:
        """ Last send/receive time """
        return self.__last_time

    def close(self):
        # disconnected
        self.__connected = False
        time.sleep(2)
        # cancel threads
        if self.__thread_receive is not None:
            self.__thread_receive = None
        if self.__thread_heartbeat is not None:
            self.__thread_heartbeat = None
        # disconnect the socket
        if self.__sock is not None:
            self.__sock.close()
            self.__sock = None

    def connect(self, station: Station):
        # connect to new socket (host:port)
        self.__station = station
        address = (station.host, station.port)
        self.__sock = socket.socket()
        self.__sock.connect(address)
        self.__connected = True
        # start threads
        self.__last_time = int(time.time())
        if self.__thread_receive is None:
            self.__thread_receive = Thread(target=receive_handler, args=(self,))
            self.__thread_receive.start()
        if self.__thread_heartbeat is None:
            self.__thread_heartbeat = Thread(target=heartbeat_handler, args=(self,))
            self.__thread_heartbeat.start()

    def reconnect(self):
        # disconnected
        if self.__sock is not None:
            self.__sock.close()
            self.__sock = None
        # connect to same station
        self.connect(station=self.__station)

    def send(self, data: bytes) -> IOError:
        try:
            self.__sock.sendall(data)
        except IOError as error:
            Log.error('failed to send data: %s' % error)
            # reconnect
            self.reconnect()
            # try again
            try:
                self.__sock.sendall(data)
            except IOError as error:
                # failed
                return error
        # send OK, record the current time
        self.__last_time = int(time.time())

    def receive(self, buffer_size=1024) -> bytes:
        data = None
        try:
            data = self.__sock.recv(buffer_size)
        except IOError as error:
            Log.error('failed to receive data: %s' % error)
            # reconnect
            self.reconnect()
            # try again
            try:
                data = self.__sock.recv(buffer_size)
            except IOError as error:
                # failed
                Log.error('failed to receive data again: %s' % error)
        if data is not None:
            # receive OK, record the current time
            self.__last_time = int(time.time())
            return data

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
        return error is None

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
            data += conn.receive()
        except OSError:
            break
        # split package(s)
        pos = data.find(conn.BOUNDARY)
        while pos != -1:
            pack = data[:pos]
            conn.delegate.receive_package(data=pack)
            # next package
            pos += len(conn.BOUNDARY)
            data = data[pos:]
            pos = data.find(conn.BOUNDARY)


def heartbeat_handler(conn: Connection):
    while conn.connected:
        time.sleep(1)
        now = int(time.time())
        delta = now - conn.last_time
        if delta > 28:
            # heartbeat after 5 minutes
            conn.send(data=b'\n')
