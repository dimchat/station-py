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
from typing import Optional

from tcp import Connection, ConnectionStatus, ConnectionDelegate
from tcp import BaseConnection, ActiveConnection

from startrek import GateStatus, StarGate
from startrek import Docker

from .ws import WSDocker
from .mtp import MTPDocker
from .mars import MarsDocker


def gate_status(status: ConnectionStatus) -> GateStatus:
    """ Convert Connection Status to Star Gate Status """
    if status in [ConnectionStatus.Connected, ConnectionStatus.Maintaining, ConnectionStatus.Expired]:
        return GateStatus.Connected
    if status == ConnectionStatus.Connecting:
        return GateStatus.Connecting
    if status == ConnectionStatus.Error:
        return GateStatus.Error
    # Default
    return GateStatus.Init


class TCPGate(StarGate, ConnectionDelegate):

    def __init__(self, connection: Connection):
        super().__init__()
        self.__conn = connection
        self.__chunks: Optional[bytes] = None

    @property
    def connection(self) -> Connection:
        return self.__conn

    # Override
    def _create_docker(self) -> Optional[Docker]:
        # override to customize Docker
        if MTPDocker.check(gate=self):
            return MTPDocker(gate=self)
        if MarsDocker.check(gate=self):
            return MarsDocker(gate=self)
        if WSDocker.check(gate=self):
            return WSDocker(gate=self)

    @property
    def running(self) -> bool:
        if super().running:
            # connection not closed or still have data unprocessed
            return self.__conn.alive or self.__conn.available > 0

    @property
    def expired(self) -> bool:
        return self.__conn.status == ConnectionStatus.Expired

    # Override
    @property
    def status(self) -> GateStatus:
        return gate_status(status=self.__conn.status)

    #
    #   Connection
    #

    # Override
    def send(self, data: bytes) -> bool:
        if self.__conn.alive:
            return self.__conn.send(data=data) == len(data)

    # Override
    def receive(self, length: int, remove: bool) -> Optional[bytes]:
        fragment = self.__receive(length=length)
        if fragment is not None:
            if len(fragment) > length:
                if remove:
                    self.__chunks = fragment[length:]
                return fragment[:length]
            elif remove:
                # assert len(fragment) == length, 'fragment length error'
                self.__chunks = None
            return fragment

    def __receive(self, length: int) -> Optional[bytes]:
        cached = 0
        if self.__chunks is not None:
            cached = len(self.__chunks)
        while cached < length:
            # check available length from connection
            available = self.__conn.available
            if available <= 0:
                break
            # try to receive data from connection
            data = self.__conn.receive(max_length=available)
            if data is None:
                break
            # append data
            if self.__chunks is None:
                self.__chunks = data
            else:
                self.__chunks += data
            cached += len(data)
        return self.__chunks

    #
    #   ConnectionDelegate
    #

    # Override
    # noinspection PyUnusedLocal
    def connection_changed(self, connection, old_status: ConnectionStatus, new_status: ConnectionStatus):
        s1 = gate_status(status=old_status)
        s2 = gate_status(status=new_status)
        if s1 != s2:
            delegate = self.delegate
            if delegate is not None:
                delegate.gate_status_changed(gate=self, old_status=s1, new_status=s2)

    # Override
    def connection_received(self, connection, data: bytes):
        # received data will be processed in run loop (StarDocker::handle),
        # do nothing here
        pass


class StarTrek(TCPGate):

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
