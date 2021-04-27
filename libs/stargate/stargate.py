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
import time
import weakref
from typing import Optional

from tcp import ConnectionStatus, Connection

from .base import gate_status
from .base import Gate, GateStatus, GateDelegate, ShipDelegate
from .base import Worker

from .ws import WSDocker
from .mtp import MTPDocker
from .mars import MarsDocker


class StarGate(Gate):

    def __init__(self, address: Optional[tuple] = None, sock: Optional[socket.socket] = None):
        super().__init__()
        if sock is None:
            # client gate
            self.__connection = Connection(address=address)
            self.__worker = MTPDocker(gate=self)
        else:
            # server gate
            self.__connection = Connection(sock=sock)
            self.__worker = None
        # set StarGate as connection delegate
        self.__connection.delegate = self
        # StarGate delegate
        self.__delegate: Optional[weakref.ReferenceType] = None

    # Override
    @property
    def status(self) -> GateStatus:
        return gate_status(status=self.connection.status)

    # Override
    @property
    def delegate(self) -> Optional[GateDelegate]:
        if self.__delegate is None:
            return None
        else:
            return self.__delegate()

    @delegate.setter
    def delegate(self, handler: GateDelegate):
        if handler is None:
            self.__delegate = None
        else:
            self.__delegate = weakref.ref(handler)

    # Override
    @property
    def connection(self) -> Optional[Connection]:
        return self.__connection

    # Override
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        if self.__worker is not None and self.status == GateStatus.Connected:
            return self.__worker.send(payload=payload, priority=priority, delegate=delegate)

    # Override
    def process(self):
        self.setup()
        try:
            while self.status != GateStatus.Error:
                self.handle()
        finally:
            self.finish()

    def setup(self):
        # 1. start connection
        self.__connection.start()
        # 2. waiting for worker
        while self.__worker is None:
            time.sleep(0.1)
            self.__worker = self._create_worker()
        # 3. setup worker
        self.__worker.setup()

    def handle(self) -> bool:
        return self.__worker.handle()

    def finish(self):
        # 1. clean worker
        self.__worker.finish()
        # 2. stop connection
        self.__connection.stop()

    # override to customize Worker
    def _create_worker(self) -> Optional[Worker]:
        conn = self.connection
        if conn is None:
            return None
        if MTPDocker.check(connection=self.connection):
            return MTPDocker(gate=self)
        if MarsDocker.check(connection=self.connection):
            return MarsDocker(gate=self)
        if WSDocker.check(connection=self.connection):
            return WSDocker(gate=self)

    #
    #   ConnectionDelegate
    #
    def connection_changed(self, connection, old_status: ConnectionStatus, new_status: ConnectionStatus):
        delegate = self.delegate
        if delegate is not None:
            s1 = gate_status(status=old_status)
            s2 = gate_status(status=new_status)
            delegate.gate_status_changed(gate=self, old_status=s1, new_status=s2)

    def connection_received(self, connection, data: bytes):
        # received data will be processed in run loop (MTPDocker::processIncome),
        # do nothing here
        pass

    def connection_overflowed(self, connection, ejected: bytes):
        # TODO: connection cache pool is full,
        #       some received data will be ejected to here,
        #       the application should try to process them.
        pass
