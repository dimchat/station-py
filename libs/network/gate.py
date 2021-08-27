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

from tcp import Channel, StreamChannel
from tcp import Connection, ConnectionState, ConnectionDelegate
from tcp import BaseConnection, ActiveConnection

from udp.ba import ByteArray, Data

from startrek import GateStatus, StarGate
from startrek import Docker

from .ws import WSDocker
from .mtp import MTPDocker
from .mars import MarsDocker


def gate_status(state: ConnectionState) -> GateStatus:
    """ Convert Connection Status to Star Gate Status """
    if state in [ConnectionState.CONNECTED, ConnectionState.MAINTAINING, ConnectionState.EXPIRED]:
        return GateStatus.Connected
    elif state == ConnectionState.CONNECTING:
        return GateStatus.Connecting
    elif state == ConnectionState.ERROR:
        return GateStatus.Error
    else:
        return GateStatus.Init


class TCPGate(StarGate, ConnectionDelegate):

    def __init__(self, connection: Connection):
        super().__init__()
        self.__conn = connection
        self.__occupied = False
        self.__chunks: Optional[ByteArray] = None

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
            # 1. StarGate not stopped
            # 2. Connection not closed
            return self.__conn.opened

    @property
    def expired(self) -> bool:
        return self.__conn.state == ConnectionState.EXPIRED

    # Override
    @property
    def status(self) -> GateStatus:
        return gate_status(state=self.__conn.state)

    #
    #   Connection
    #

    # Override
    def send(self, data: bytes) -> bool:
        if not self.__conn.opened or not self.__conn.connected:
            return False
        try:
            return self.__conn.send(data=data) != -1
        except socket.error:
            return False

    # Override
    def receive(self, length: int, remove: bool) -> Optional[bytes]:
        if self.__occupied:
            return None
        else:
            self.__occupied = True
            fragment = self.__receive(length=length)
            self.__occupied = False
        if fragment is None:
            return None
        elif fragment.size > length:
            if remove:
                # fragment[length:]
                self.__chunks = fragment.slice(start=length)
            # fragment[:length]
            fragment = fragment.slice(start=0, end=length)
        elif remove:
            # assert len(fragment) == length, 'fragment length error'
            self.__chunks = None
        return fragment.get_bytes()

    def __receive(self, length: int) -> Optional[ByteArray]:
        if self.__chunks is None:
            size = 0
        else:
            size = self.__chunks.size
        prev = -1
        while prev < size < length:
            prev = size
            # drive the connection to receive data
            self.__conn.tick()
            # get next received data size
            if self.__chunks is None:
                size = 0
            else:
                size = self.__chunks.size
        return self.__chunks

    #
    #   ConnectionDelegate
    #

    # Override
    def connection_state_changed(self, connection: Connection, previous, current):
        s1 = gate_status(state=previous)
        s2 = gate_status(state=current)
        if s1 != s2:
            delegate = self.delegate
            if delegate is not None:
                delegate.gate_status_changed(gate=self, old_status=s1, new_status=s2)

    # Override
    def connection_data_received(self, connection: Connection, remote: tuple, wrapper, payload):
        if not isinstance(payload, ByteArray):
            payload = Data(buffer=payload)
        fragment = self.__chunks
        if fragment is None or fragment.size == 0:
            self.__chunks = payload
        else:
            self.__chunks = fragment.concat(payload)


class LockedGate(TCPGate):

    def __init__(self, connection: Connection):
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


class StarTrek(LockedGate):

    def __init__(self, connection: Connection):
        super().__init__(connection=connection)

    @classmethod
    def create_gate(cls, address: Optional[tuple] = None, sock: Optional[socket.socket] = None) -> StarGate:
        print('!!! create gate: (%s) %s' % (address, sock))
        if sock is None:
            assert address is not None, 'remote address should not be emtpy'
            conn = ActiveStreamConnection(remote=address)
        else:
            conn = StreamConnection(sock=sock)
        # create gate with connection
        gate = StarTrek(connection=conn)
        conn.delegate = gate
        return gate

    def start(self):
        conn = self.connection
        assert isinstance(conn, BaseConnection), 'connection error: %s' % conn
        conn.start()
        threading.Thread(target=self.run).start()

    # Override
    def process(self) -> bool:
        self.connection.tick()
        return super().process()

    # Override
    def finish(self):
        super().finish()
        conn = self.connection
        assert isinstance(conn, BaseConnection), 'connection error: %s' % conn
        conn.stop()


class StreamConnection(BaseConnection):
    """ Stream Connection """

    def __init__(self, sock: socket.socket):
        # create channel with socket
        channel = StreamChannel(sock=sock)
        channel.configure_blocking(blocking=False)
        super().__init__(remote=channel.remote_address, local=channel.local_address, channel=channel)


class ActiveStreamConnection(ActiveConnection):
    """ Active Stream Connection """

    def __init__(self, remote: tuple):
        super().__init__(remote=remote, local=None, channel=None)

    def connect(self, remote: tuple, local: Optional[tuple] = None) -> Channel:
        channel = StreamChannel(remote=remote, local=local)
        channel.configure_blocking(blocking=False)
        return channel
