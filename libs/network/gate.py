# -*- coding: utf-8 -*-
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
from typing import Optional

from tcp import BaseConnection, ActiveConnection

from startrek import StarGate
from startrek import Docker

from .ws import WSDocker
from .mtp import MTPDocker
from .mars import MarsDocker


class StarTrek(StarGate):

    @classmethod
    def create(cls, address: Optional[tuple] = None, sock: Optional[socket.socket] = None) -> StarGate:
        if address is None:
            conn = BaseConnection(sock=sock)
        else:
            conn = ActiveConnection(address=address, sock=sock)
        gate = StarTrek(connection=conn)
        conn.delegate = gate
        return gate

    def __init__(self, connection: BaseConnection):
        super().__init__(connection=connection)
        self.__send_lock = threading.RLock()
        self.__receive_lock = threading.RLock()

    # Override
    def _create_docker(self) -> Optional[Docker]:
        # override to customize Docker
        if MTPDocker.check(gate=self):
            return MTPDocker(gate=self)
        if MarsDocker.check(gate=self):
            return MarsDocker(gate=self)
        if WSDocker.check(gate=self):
            return WSDocker(gate=self)

    # Override
    def send(self, data: bytes) -> bool:
        with self.__send_lock:
            return super().send(data=data)

    # Override
    def receive(self, length: int, remove: bool) -> Optional[bytes]:
        with self.__receive_lock:
            return super().receive(length=length, remove=remove)

    # Override
    def setup(self):
        conn = self.connection
        assert isinstance(conn, BaseConnection), 'connection error: %s' % conn
        threading.Thread(target=conn.run).start()
        super().setup()

    # Override
    def finish(self):
        super().finish()
        conn = self.connection
        assert isinstance(conn, BaseConnection), 'connection error: %s' % conn
        conn.stop()
