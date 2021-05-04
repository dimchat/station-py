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

from tcp import BaseConnection, ActiveConnection, ConnectionDelegate

from ...stargate import StarGate as BaseGate
from ...stargate import Docker

from .ws import WSDocker
from .mtp import MTPDocker
from .mars import MarsDocker


def create_connection(delegate: ConnectionDelegate,
                      address: Optional[tuple] = None,
                      sock: Optional[socket.socket] = None) -> BaseConnection:
    if address is None:
        conn = BaseConnection(sock=sock)
    else:
        conn = ActiveConnection(address=address, sock=sock)
    conn.delegate = delegate
    return conn


class StarGate(BaseGate):

    def __init__(self, address: Optional[tuple] = None, sock: Optional[socket.socket] = None):
        conn = create_connection(delegate=self, address=address, sock=sock)
        super().__init__(connection=conn)
        self.__conn = conn

    # Override
    def _create_docker(self) -> Optional[Docker]:
        # override to customize Docker
        if MTPDocker.check(connection=self.__conn):
            return MTPDocker(gate=self)
        if MarsDocker.check(connection=self.__conn):
            return MarsDocker(gate=self)
        if WSDocker.check(connection=self.__conn):
            return WSDocker(gate=self)

    # Override
    def setup(self):
        threading.Thread(target=self.__conn.run).start()
        super().setup()

    # Override
    def finish(self):
        super().finish()
        self.__conn.stop()
