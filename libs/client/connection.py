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
import traceback
from typing import Optional, Union

from dimp import InstantMessage
from dimsdk import Station, CompletionHandler, MessengerDelegate

from ..common import Log


class Connection(threading.Thread, MessengerDelegate):

    # boundary for packages
    BOUNDARY = b'\n'

    def __init__(self):
        super().__init__()
        self.messenger = None  # ClientMessenger
        # current station
        self.__address = None
        self.__connected = False
        self.__running = False
        # socket
        self.__sock = None
        self.__thread_heartbeat = None
        self.__last_time: int = 0

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def __del__(self):
        self.disconnect()

    def start(self):
        if not self.__running:
            self.__running = True
            super().start()

    def stop(self):
        if self.__running:
            self.__running = False

    def run(self):
        data = b''
        while self.__running:
            if not self.__connected:
                time.sleep(0.5)
                continue
            # receive all data
            remaining_length = len(data)
            data = self.receive(data=data)
            if len(data) == remaining_length:
                self.info('no more data, remaining=%d' % remaining_length)
                time.sleep(0.5)
                continue
            # check whether contain incomplete message
            pos = data.find(self.BOUNDARY)
            while pos >= 0:
                pack = data[:pos]
                pos += len(self.BOUNDARY)
                data = data[pos:]
                # maybe more than one message in a time
                self.__received_package(pack=pack)
                pos = data.find(self.BOUNDARY)
                # partially package? keep it for next loop

    def __received_package(self, pack: bytes):
        lines = pack.splitlines()
        pack = b''
        for line in lines:
            line = line.strip()
            if len(line) == 0:
                # skip empty packages
                continue
            try:
                res = self.messenger.process_package(data=line)
                if res is not None:
                    pack = pack + res + b'\n'
            except Exception as error:
                self.error('receive package error: %s' % error)
                traceback.print_exc()
        if len(pack) > 0:
            self.send(data=pack)

    def disconnect(self):
        self.__connected = False
        # cancel threads
        if self.__thread_heartbeat is not None:
            self.__thread_heartbeat = None
        # disconnect the socket
        if self.__sock is not None:
            self.__sock.close()
            self.__sock = None

    def connect(self, server: Union[Station, tuple]):
        # connect to new socket (host:port)
        if isinstance(server, Station):
            address = (server.host, server.port)
        else:
            address = server
        self.info('Connecting: (%s:%d) ...' % address)
        self.__address = address
        self.__sock = socket.socket()
        self.__sock.connect(self.__address)
        self.__connected = True
        self.info('DIM Station %s connected.' % server)
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
        self.connect(server=self.__address)

    def heartbeat(self):
        while self.__connected:
            time.sleep(1)
            now = int(time.time())
            delta = now - self.__last_time
            if delta > 28:
                # heartbeat after 5 minutes
                self.send(data=b'\n')

    #
    #   Socket IO
    #
    def __receive(self, data: bytes=b'') -> bytes:
        while True:
            try:
                part = self.__sock.recv(1024)
            except IOError as error:
                self.error('failed to receive data %s' % error)
                part = None
            if part is None:
                break
            data += part
            if len(part) < 1024:
                break
        return data

    def __send(self, data: bytes) -> IOError:
        try:
            self.__sock.sendall(data)
        except IOError as error:
            self.error('failed to send data %s' % error)
            return error

    def send(self, data: bytes) -> IOError:
        error = self.__send(data=data)
        if error is not None:
            self.reconnect()
            # try again
            error = self.__send(data=data)
            if error is not None:
                # failed
                self.error('failed to send data again: %s' % error)
                self.__connected = False
                return error
        # send OK, record the current time
        self.__last_time = int(time.time())

    def receive(self, data: bytes=b'') -> bytes:
        remaining_len = len(data)
        data = self.__receive(data=data)
        if len(data) == remaining_len:
            self.reconnect()
            # try again
            data = self.__receive(data=data)
            if len(data) == remaining_len:
                # failed
                self.error('failed to receive data again')
                self.__connected = False
        if len(data) > remaining_len:
            # receive OK, record the current time
            self.__last_time = int(time.time())
        return data

    #
    #   MessengerDelegate
    #
    def send_package(self, data: bytes, handler: CompletionHandler) -> bool:
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

    def download_data(self, url: str, msg: InstantMessage) -> Optional[bytes]:
        """ Download encrypted data from CDN, and decrypt it when finished """
        pass
