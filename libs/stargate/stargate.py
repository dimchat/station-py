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
import traceback
from typing import Optional

from dmtp.mtp import Package
from dmtp.mtp import Message as MTPMessage
from dmtp.mtp.tlv import Data
from tcp import Connection, ConnectionStatus

from .base import gate_status
from .base import Gate, GateStatus, GateDelegate
from .docker import Docker
from .stardocker import StarDocker
from .starship import StarShip


class StarGate(threading.Thread, Gate):

    def __init__(self, delegate: GateDelegate):
        super().__init__()
        self.__worker = self._create_worker(delegate=delegate)
        # thread
        self.__started = False
        self.__running = False

    def _create_worker(self, delegate: GateDelegate) -> Docker:
        # override for customized worker
        return StarDocker(gate=self, delegate=delegate)

    @property
    def status(self) -> GateStatus:
        s = self.__worker.status
        return gate_status(status=s)

    # Override
    def open(self, host: str, port: int, sock: Optional[socket.socket] = None) -> Optional[socket.error]:
        return self.__worker.connect(host=host, port=port, sock=sock)

    # Override
    def close(self):
        self.__worker.disconnect()

    # Override
    def send(self, payload: bytes, priority: int, delegate: Optional[GateDelegate]):
        req = Data(data=payload)
        pack = Package.new(data_type=MTPMessage, body_length=req.length, body=req)
        ship = StarShip(package=pack)
        self.__worker.add_task(ship=ship)

    def start(self):
        # check running
        tick = 0
        while self.__running:
            # waiting for last run loop exit
            time.sleep(0.1)
            tick += 1
            if tick > 100:
                # timeout (10 seconds)
                break
        # do start
        if not self.__started:
            super().start()

    def stop(self):
        self.__started = False
        self.close()

    def run(self):
        self.__started = True
        self.__running = True
        count = 0
        while self.__started:
            try:
                count = self.__worker.process(count=count)
            except Exception as error:
                print('[StarGate] process error: %s' % error)
                traceback.print_exc()
        # stop running
        self.__running = False

    #
    #   ConnectionHandler
    #
    def connection_status_changed(self, connection: Connection,
                                  old_status: ConnectionStatus, new_status: ConnectionStatus):
        delegate = self.__worker.delegate
        if delegate is not None:
            s1 = gate_status(status=old_status)
            s2 = gate_status(status=new_status)
            delegate.gate_status_changed(gate=self, old_status=s1, new_status=s2)

    def connection_received_data(self, connection: Connection):
        # received data will be processed in run loop (StarDocker::processIncome),
        # do nothing here
        pass

    def connection_overflowed(self, connection: Connection, ejected: bytes):
        # TODO: connection cache pool is full,
        #       some received data will be ejected to here,
        #       the application should try to process them.
        pass
