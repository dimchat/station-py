# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
#
#                                Written in 2021 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

import socket
import threading
import time
import weakref
from typing import Optional

from tcp import ConnectionStatus, Connection, ClientConnection, ServerConnection

from .base import gate_status
from .base import Gate, GateStatus, GateDelegate
from .base import Worker

from .mtp import MTPDocker
from .mars import MarsDocker


class StarGate(Gate):

    def __init__(self, delegate: GateDelegate):
        super().__init__()
        self.__delegate = weakref.ref(delegate)
        self.__worker: Optional[Worker] = None
        # socket connection
        self.__connection: Optional[Connection] = None
        self.__connection_lock = threading.Lock()

    # Override
    @property
    def status(self) -> GateStatus:
        conn = self.__connection
        if conn is None:
            return GateStatus.Init
        else:
            return gate_status(status=conn.status)

    # Override
    @property
    def delegate(self) -> Optional[GateDelegate]:
        return self.__delegate()

    @property
    def worker(self) -> Optional[Worker]:
        return self.__worker

    @worker.setter
    def worker(self, docker: Worker):
        self.__worker = docker

    # Override
    @property
    def connection(self) -> Optional[Connection]:
        return self.__connection

    # override for customized Connection
    def _create_client_connection(self, address: tuple) -> Optional[Connection]:
        conn = self.__connection
        if conn is None or conn.address != address:
            return ClientConnection(address=address)

    # override for customized Connection
    def _create_server_connection(self, sock: socket.socket) -> Optional[Connection]:
        conn = self.__connection
        if conn is None or conn.socket != sock:
            return ServerConnection(sock=sock)

    def __connect(self, address: Optional[tuple] = None, sock: Optional[socket.socket] = None) -> Optional[Connection]:
        if sock is not None:
            conn = self._create_server_connection(sock=sock)
        else:
            assert isinstance(address, tuple), 'address error: %s' % str(address)
            conn = self._create_client_connection(address=address)
            # as a client, always use MTP docker for packing data
            if not isinstance(self.__worker, MTPDocker):
                self.__worker = MTPDocker(gate=self)
        if conn is not None:
            self.__disconnect()
            conn.delegate = self
            conn.start()
            self.__connection = conn
        return self.__connection

    def __disconnect(self):
        if self.__connection is not None:
            self.__connection.stop()
            self.__connection = None

    # Override
    def open(self, address: Optional[tuple] = None, sock: Optional[socket.socket] = None) -> Optional[Connection]:
        with self.__connection_lock:
            return self.__connect(address=address, sock=sock)

    # Override
    def close(self):
        with self.__connection_lock:
            self.__disconnect()

    # Override
    def send(self, payload: bytes, priority: int, delegate: Optional[GateDelegate]) -> bool:
        if self.__worker is None:
            return False
        if self.status != GateStatus.Connected:
            # not connect yet
            return False
        return self.__worker.send(payload=payload, priority=priority, delegate=delegate)

    # Override
    def process(self):
        # 1. waiting for worker
        self.setup()
        try:
            # 2. process by worker
            self.handle()
        finally:
            # 3. clean up by worker
            self.finished()

    def setup(self):
        while self.worker is None:
            time.sleep(0.1)
            if MTPDocker.check(connection=self.connection):
                self.worker = MTPDocker(gate=self)
            elif MarsDocker.check(connection=self.connection):
                self.worker = MarsDocker(gate=self)

    def handle(self):
        count = 0
        while self.status != GateStatus.Error:
            count = self.worker.process(counter=count)

    def finished(self):
        self.worker.clean()

    #
    #   ConnectionHandler
    #
    def connection_status_changed(self, connection: Connection,
                                  old_status: ConnectionStatus, new_status: ConnectionStatus):
        delegate = self.delegate
        if delegate is not None:
            s1 = gate_status(status=old_status)
            s2 = gate_status(status=new_status)
            delegate.gate_status_changed(gate=self, old_status=s1, new_status=s2)

    def connection_received_data(self, connection: Connection):
        # received data will be processed in run loop (MTPDocker::processIncome),
        # do nothing here
        pass

    def connection_overflowed(self, connection: Connection, ejected: bytes):
        # TODO: connection cache pool is full,
        #       some received data will be ejected to here,
        #       the application should try to process them.
        pass
