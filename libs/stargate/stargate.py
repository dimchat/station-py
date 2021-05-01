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

import time
import weakref
from typing import Optional

from tcp import Connection, ConnectionStatus, ConnectionDelegate
from tcp import BaseConnection

from .ship import ShipDelegate
from .dock import Dock
from .worker import Worker
from .gate import gate_status
from .gate import Gate, GateStatus, GateDelegate

from .ws import WSDocker
from .mtp import MTPDocker
from .mars import MarsDocker


class StarGate(Gate, ConnectionDelegate):

    def __init__(self, connection: Connection):
        super().__init__()
        self.__dock = Dock()
        self.__connection = connection
        self.__worker: Optional[Worker] = None
        self.__delegate: Optional[weakref.ReferenceType] = None
        self._running = False

    # Override
    @property
    def dock(self) -> Dock:
        return self.__dock

    # Override
    @property
    def connection(self) -> Connection:
        return self.__connection

    # Override
    @property
    def worker(self) -> Optional[Worker]:
        if self.__worker is None:
            self.__worker = self._create_worker()
        return self.__worker

    # override to customize Worker
    def _create_worker(self) -> Optional[Worker]:
        if MTPDocker.check(connection=self.connection):
            return MTPDocker(gate=self)
        if MarsDocker.check(connection=self.connection):
            return MarsDocker(gate=self)
        if WSDocker.check(connection=self.connection):
            return WSDocker(gate=self)

    @worker.setter
    def worker(self, docker: Worker):
        self.__worker = docker

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
    def status(self) -> GateStatus:
        cs = self.connection.status
        return gate_status(status=cs)

    # Override
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        worker = self.worker
        if worker is None:
            return False
        if self.status != GateStatus.Connected:
            return False
        return worker.send(payload=payload, priority=priority, delegate=delegate)

    #
    #   Running
    #

    def run(self):
        # start connection
        while self.status in [GateStatus.Init, GateStatus.Connecting]:
            # waiting for connection
            self._idle()
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def stop(self):
        self._running = False

    def setup(self):
        self._running = True
        # check worker
        while self.worker is None and not self.connection_finished:
            # waiting for worker
            self._idle()
        # setup worker
        if self.__worker is not None:
            self.__worker.setup()

    def finish(self):
        # clean worker
        if self.__worker is not None:
            self.__worker.finish()

    @property
    def connection_finished(self) -> bool:
        """ connection closed, and no more data unpressed """
        conn = self.__connection
        assert isinstance(conn, BaseConnection), 'connection error: %s' % conn
        if not conn.running and conn.received() is None:
            return True

    @property
    def running(self) -> bool:
        return self._running and not self.connection_finished

    # Override
    def handle(self):
        while self.running:
            if not self.process():
                self._idle()

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.1)

    def process(self) -> bool:
        if self.__worker is not None:
            return self.__worker.process()

    #
    #   ConnectionDelegate
    #
    def connection_changed(self, connection, old_status: ConnectionStatus, new_status: ConnectionStatus):
        delegate = self.delegate
        if delegate is not None:
            s1 = gate_status(status=old_status)
            s2 = gate_status(status=new_status)
            if s1 != s2:
                delegate.gate_status_changed(gate=self, old_status=s1, new_status=s2)

    def connection_received(self, connection, data: bytes):
        # received data will be processed in run loop (Docker::handle),
        # do nothing here
        pass

    def connection_overflowed(self, connection, ejected: bytes):
        # TODO: connection cache pool is full,
        #       some received data will be ejected to here,
        #       the application should try to process them.
        pass
