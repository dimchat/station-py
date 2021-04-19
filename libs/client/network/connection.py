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
import weakref
from typing import Optional

from ...common import Connection, ConnectionDelegate


class ClientConnection(Connection):

    # time interval for maintaining connection
    HEARTBEAT_INTERVAL = 28  # second(s)

    def __init__(self, host: str, port: int = 9394):
        super().__init__()
        self.__delegate: Optional[weakref.ReferenceType] = None
        self.__messenger: Optional[weakref.ReferenceType] = None
        # current station
        self.__host = host
        self.__port = port
        self.__connected = False
        # socket
        self.__sock = None
        self.__sock_lock = threading.Lock()
        self.__thread_heartbeat = None
        self.__last_time: int = 0

    @property
    def delegate(self) -> Optional[ConnectionDelegate]:
        if self.__delegate:
            return self.__delegate()

    @delegate.setter
    def delegate(self, handler: ConnectionDelegate):
        self.__delegate = weakref.ref(handler)

    @property
    def messenger(self):  # -> ClientMessenger:
        if self.__messenger is not None:
            return self.__messenger()

    @messenger.setter
    def messenger(self, transceiver):
        self.__messenger = weakref.ref(transceiver)

    def __del__(self):
        self.disconnect()

    def disconnect(self):
        self.__connected = False
        # cancel threads
        if self.__thread_heartbeat is not None:
            self.__thread_heartbeat = None
        # disconnect the socket
        with self.__sock_lock:
            if self.__sock is not None:
                self.__sock.close()
                self.__sock = None

    def __connect(self) -> Optional[socket.error]:
        with self.__sock_lock:
            if self.__sock is not None:
                self.error('socket already connected: %s' % self.__sock)
                return None
            # connect to new socket (host:port)
            host = self.__host
            port = self.__port
            try:
                self.info('Connecting: (%s:%d) ...' % (host, port))
                sock = socket.socket()
                sock.connect((host, port))
                self.__sock = sock
                self.info('DIM Station (%s:%d) connected.' % (host, port))
            except socket.error as error:
                self.error('failed to connect (%s:%d): %s' % (host, port, error))
                return error

    def connect(self) -> Optional[socket.error]:
        error = self.__connect()
        if error is not None:
            return error
        self.__connected = True
        # start threads
        self.__last_time = int(time.time())
        if self.__thread_heartbeat is None:
            self.__thread_heartbeat = threading.Thread(target=ClientConnection.heartbeat, args=(self,))
            self.__thread_heartbeat.start()
        # on connected
        self.delegate.connection_connected(connection=self)

    def reconnect(self) -> Optional[socket.error]:
        # disconnect
        if self.__connected:
            self.disconnect()
            time.sleep(2)
        # connect to same station
        return self.connect()

    def heartbeat(self):
        while self.__connected:
            time.sleep(1)
            now = int(time.time())
            delta = now - self.__last_time
            if delta > self.HEARTBEAT_INTERVAL:
                # heartbeat after 8 seconds
                self.sendall(data=b'\n')

    def run(self):
        self.connect()
        super().run()

    #
    #   Socket
    #

    def get_socket(self) -> socket.socket:
        if self.__sock is None:
            self.reconnect()
        return self.__sock

    def sendall(self, data: bytes) -> bool:
        ok = super().sendall(data=data)
        if not ok:
            # connection lost, try to reconnect
            error = self.reconnect()
            if error is not None:
                self.error('reconnect failed, cannot send data(%d) now: %s' % (len(data), error))
                return False
            # reconnect success, send again
            ok = super().sendall(data=data)
            if not ok:
                # failed
                self.error('failed to send data again: %s' % error)
                self.disconnect()
                return False
        # send OK, record the current time
        self.__last_time = int(time.time())
        return ok

    def receive(self) -> bytes:
        data = super().receive()
        if data is None:
            # connection lost, try to reconnect
            error = self.reconnect()
            if error is not None:
                self.error('reconnect failed, cannot receive data now: %s' % error)
                return b''
            # reconnect success, receive again
            data = super().receive()
            if data is None:
                # failed
                self.error('failed to receive data again')
                self.disconnect()
                return b''
        if len(data) > 0:
            # receive OK, record the current time
            self.__last_time = int(time.time())
        return data
