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
import threading
import time
from abc import ABCMeta, abstractmethod

from dimp import Station, ITransceiverDelegate, ICompletionHandler
from dimp import InstantMessage

from ..common import Log


class IConnectionDelegate(metaclass=ABCMeta):

    @abstractmethod
    def receive_package(self, data: bytes):
        """ Receive data package

        :param data: data package
        :return:
        """
        pass


class Connection(threading.Thread, ITransceiverDelegate):

    # boundary for packages
    BOUNDARY = b'\n'

    def __init__(self):
        super().__init__()
        self.__running = threading.Event()
        self.delegate: IConnectionDelegate = None
        # current station
        self.__station: Station = None
        self.__connected = False
        # socket
        self.__sock = None
        self.__thread_heartbeat = None
        self.__last_time: int = 0

    def __del__(self):
        self.disconnect()

    def start(self):
        if not self.__running.isSet():
            self.__running.set()
            super().start()

    def stop(self):
        if self.__running.isSet():
            self.__running.clear()

    def run(self):
        data = b''
        while self.__running.isSet():
            if not self.__connected:
                time.sleep(0.5)
                continue
            # read all data
            try:
                data += self.receive()
            except IOError:
                continue
            # split package(s)
            pos = data.find(self.BOUNDARY)
            while pos != -1:
                pack = data[:pos]
                self.receive_package(data=pack)
                # next package
                pos += len(self.BOUNDARY)
                data = data[pos:]
                pos = data.find(self.BOUNDARY)

    def disconnect(self):
        self.__connected = False
        # cancel threads
        self.stop()
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
        if self.__thread_heartbeat is None:
            self.__thread_heartbeat = threading.Thread(target=Connection.heartbeat, args=(self,))
            self.__thread_heartbeat.start()
        self.start()

    def reconnect(self):
        # disconnected
        if self.__sock is not None:
            self.__sock.close()
            self.__sock = None
        # connect to same station
        self.connect(station=self.__station)

    def heartbeat(self):
        while self.__connected:
            time.sleep(1)
            now = int(time.time())
            delta = now - self.__last_time
            if delta > 28:
                # heartbeat after 5 minutes
                self.send(data=b'\n')

    def send(self, data: bytes) -> IOError:
        try:
            self.__sock.sendall(data)
        except IOError as error:
            Log.error('failed to send data: %s' % error)
            if not self.__connected:
                return error
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
            if not self.__connected:
                return b''
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

    def receive_package(self, data: bytes):
        try:
            self.delegate.receive_package(data=data)
        except Exception as error:
            Log.error('receive package error: %s' % error)

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
