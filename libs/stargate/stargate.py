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

import threading
import time
import weakref
from typing import Optional

from tcp import Connection, ConnectionStatus, ConnectionDelegate

from .ship import ShipDelegate
from .starship import StarShip
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
        self.__lock = threading.RLock()
        self.__worker: Optional[Worker] = None
        self.__delegate: Optional[weakref.ReferenceType] = None
        self.__running = False

    @property
    def connection(self) -> Connection:
        return self.__connection

    # Override
    @property
    def worker(self) -> Optional[Worker]:
        if self.__worker is None:
            self.__worker = self._create_worker()
        return self.__worker

    def _create_worker(self) -> Optional[Worker]:
        # override to customize Worker
        if MTPDocker.check(connection=self.__connection):
            return MTPDocker(gate=self)
        if MarsDocker.check(connection=self.__connection):
            return MarsDocker(gate=self)
        if WSDocker.check(connection=self.__connection):
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
        assert self.__connection is not None, 'connection should not empty'
        return gate_status(status=self.__connection.status)

    # Override
    def send_payload(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        worker = self.worker
        if worker is None:
            return False
        if self.status != GateStatus.Connected:
            return False
        req = worker.pack(payload=payload, priority=priority, delegate=delegate)
        if priority < 0:
            # send out directly
            return self.send(data=req.package)
        else:
            # put the Ship into a waiting queue
            return self.park_ship(ship=req)

    #
    #   Connection
    #

    # Override
    def send(self, data: bytes) -> bool:
        assert self.__connection is not None, 'connection should not empty'
        with self.__lock:
            return self.__connection.send(data=data) == len(data)

    # Override
    def received(self) -> Optional[bytes]:
        assert self.__connection is not None, 'connection should not empty'
        return self.__connection.received()

    # Override
    def receive(self, length: int) -> Optional[bytes]:
        assert self.__connection is not None, 'connection should not empty'
        return self.__connection.receive(length=length)

    #
    #   Docking
    #

    # Override
    def park_ship(self, ship: StarShip) -> bool:
        return self.__dock.put(ship=ship)

    # Override
    def pull_ship(self, sn: Optional[bytes] = None) -> Optional[StarShip]:
        return self.__dock.pop(sn=sn)

    # Override
    def any_ship(self) -> Optional[StarShip]:
        return self.__dock.any()

    #
    #   Running
    #

    def run(self):
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def stop(self):
        self.__running = False

    @property
    def opened(self) -> bool:
        if self.__running:
            conn = self.__connection
            # connection not closed or still have data unprocessed
            return conn.alive or conn.received() is not None

    def setup(self):
        self.__running = True
        if not self.opened:
            # waiting for connection
            self._idle()
        # check worker
        while self.worker is None and self.opened:
            # waiting for worker
            self._idle()
        # setup worker
        worker = self.worker
        if worker is not None:
            worker.setup()

    def finish(self):
        # clean worker
        if self.__worker is not None:
            self.__worker.finish()

    # Override
    def handle(self):
        while self.opened:
            if not self.process():
                self._idle()

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.1)

    def process(self) -> bool:
        if self.__worker is None:
            raise AssertionError('Star worker not found!')
        else:
            return self.__worker.process()

    #
    #   ConnectionDelegate
    #

    # Override
    def connection_changed(self, connection, old_status: ConnectionStatus, new_status: ConnectionStatus):
        delegate = self.delegate
        if delegate is not None:
            s1 = gate_status(status=old_status)
            s2 = gate_status(status=new_status)
            if s1 != s2:
                delegate.gate_status_changed(gate=self, old_status=s1, new_status=s2)

    # Override
    def connection_received(self, connection, data: bytes):
        # received data will be processed in run loop (Docker::handle),
        # do nothing here
        pass

    # Override
    def connection_overflowed(self, connection, ejected: bytes):
        # TODO: connection cache pool is full,
        #       some received data will be ejected to here,
        #       the application should try to process them.
        pass
