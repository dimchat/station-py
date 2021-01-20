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
import weakref
from typing import Optional

from libs.utils import Log


class Connection(threading.Thread):

    # boundary for packages
    BOUNDARY = b'\n'

    def __init__(self):
        super().__init__()
        self.__messenger: weakref.ReferenceType = None
        # current station
        self.__host = None
        self.__port = 9394
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

    @property
    def messenger(self):  # -> ClientMessenger:
        if self.__messenger is not None:
            return self.__messenger()

    @messenger.setter
    def messenger(self, transceiver):
        self.__messenger = weakref.ref(transceiver)

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
            data = self.receive(last=data)
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
                self.error('failed to process package (%s): %s' % (error, line))
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

    def connect(self, host: str, port: int=9394) -> Optional[socket.error]:
        # connect to new socket (host:port)
        sock = socket.socket()
        try:
            self.info('Connecting: (%s:%d) ...' % (host, port))
            sock.connect((host, port))
            self.info('DIM Station (%s:%d) connected.' % (host, port))
        except socket.error as error:
            self.error('failed to connect (%s:%d): %s' % (host, port, error))
            return error
        self.__host = host
        self.__port = port
        self.__sock = sock
        self.__connected = True
        # start threads
        self.__last_time = int(time.time())
        if self.__thread_heartbeat is None:
            self.__thread_heartbeat = threading.Thread(target=Connection.heartbeat, args=(self,))
            self.__thread_heartbeat.start()
        self.start()

    def reconnect(self) -> Optional[socket.error]:
        # disconnect
        if self.__connected:
            self.disconnect()
            time.sleep(2)
        # connect to same station
        return self.connect(host=self.__host, port=self.__port)

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
    def __receive(self, data: bytes=b'') -> Optional[bytes]:
        while True:
            if self.__sock is None:
                self.disconnect()
                break
            try:
                part = self.__sock.recv(1024)
            except socket.error as error:
                self.error('failed to receive data: %s' % error)
                return None
            if part is None:
                break
            data += part
            if len(part) < 1024:
                break
        return data

    def __send(self, data: bytes) -> Optional[socket.error]:
        if self.__sock is None:
            self.disconnect()
            return socket.error('socket not connect')
        try:
            self.__sock.sendall(data)
        except socket.error as error:
            self.error('failed to send data: %s' % error)
            return error

    def send(self, data: bytes) -> socket.error:
        error = self.__send(data=data)
        if error is not None:
            # connection lost, try to reconnect
            error = self.reconnect()
            if error is not None:
                self.error('reconnect failed, cannot send data(%d) now: %s' % (len(data), error))
                return error
            # reconnect success, send message
            error = self.__send(data=data)
            if error is not None:
                # failed
                self.error('failed to send data again: %s' % error)
                self.disconnect()
                return error
        # send OK, record the current time
        self.__last_time = int(time.time())

    def receive(self, last: bytes=b'') -> bytes:
        data = self.__receive(data=last)
        if data is None:
            # connection lost, try to reconnect
            error = self.reconnect()
            if error is not None:
                self.error('reconnect failed, cannot receive data now: %s' % error)
                return b''
            # try again
            data = self.__receive(data=last)
            if data is None:
                # failed
                self.error('failed to receive data again')
                self.disconnect()
                return b''
        if len(data) > len(last):
            # receive OK, record the current time
            self.__last_time = int(time.time())
        return data
