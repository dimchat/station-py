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
from abc import abstractmethod
from enum import IntEnum
from typing import Optional

from tcp import ConnectionStatus, ConnectionHandler


class GateStatus(IntEnum):
    """ Star Gate Status """

    Error = -1
    Init = 0
    Connecting = 1
    Connected = 2


def gate_status(status: ConnectionStatus) -> GateStatus:
    """ Convert Connection Status to Star Gate Status """
    if status in [ConnectionStatus.Default, ConnectionStatus.Connecting]:
        return GateStatus.Connecting
    if status in [ConnectionStatus.Connected, ConnectionStatus.Maintaining, ConnectionStatus.Expired]:
        return GateStatus.Connected
    if status == ConnectionStatus.Error:
        return GateStatus.Error
    return GateStatus.Init


class GateDelegate:
    """ Star Gate Delegate """

    # @abstractmethod
    def gate_status_changed(self, gate, old_status: GateStatus, new_status: GateStatus):
        """
        Callback when connection status changed

        :param gate:       remote gate
        :param old_status: last status
        :param new_status: current status
        """
        pass

    @abstractmethod
    def gate_received(self, gate, payload: bytes):
        """
        Callback when new package received

        :param gate:       remote gate
        :param payload:    received data
        """
        raise NotImplemented

    # @abstractmethod
    def gate_sent(self, gate, payload: bytes, error: Optional[OSError]):
        """
        Callback when package sent

        :param gate:       remote gate
        :param payload:    request data
        :param error:      None on success
        """
        pass


class Ship:
    """ Star Ship for carrying data """

    @property
    def payload(self) -> bytes:
        """ Get data in this Star Ship """
        raise NotImplemented


class OutgoShip(Ship):
    """ Star Ship carrying package to remote Star Gate """

    # retry
    EXPIRES = 120  # 2 minutes
    RETRIES = 2

    # priority
    URGENT = -1
    NORMAL = 0
    SLOWER = 1

    @property
    def delegate(self) -> Optional[GateDelegate]:
        """ Get Gate handler for this Star Ship """
        yield None

    @property
    def priority(self) -> int:
        """ Get priority of this Star Ship """
        return 0

    @property
    def time(self) -> int:
        """ Get last time of trying """
        raise NotImplemented

    @property
    def retries(self) -> int:
        """ Get count of retries """
        raise NotImplemented

    def update(self):
        """ Update retries count and time """
        raise NotImplemented


class Worker:
    """ Star Worker for packages in Ships to the remote Star Gate """

    # flow control
    MAX_INCOMES_PER_OUTGO = 4
    # seconds
    INCOME_INTERVAL = 8.0 / 1000.0
    OUTGO_INTERVAL = 32.0 / 1000.0
    IDLE_INTERVAL = 256.0 / 1000.0

    @property
    def delegate(self) -> Optional[GateDelegate]:
        """ Get default Gate handler """
        yield None

    @property
    def status(self) -> ConnectionStatus:
        """ Get Connection Status """
        raise NotImplemented

    @abstractmethod
    def connect(self, host: str, port: int, sock: Optional[socket.socket] = None) -> Optional[socket.error]:
        """ Start connection """
        raise NotImplemented

    @abstractmethod
    def disconnect(self):
        """ Stop connection """
        raise NotImplemented

    @abstractmethod
    def add_task(self, ship: OutgoShip):
        """ Put this Ship in a queue for sending out """
        raise NotImplemented

    @abstractmethod
    def process(self, count: int) -> int:
        """ Process incoming/outgoing Ships """
        raise NotImplemented


class Gate(ConnectionHandler):
    """ Star Gate of remote peer """

    @property
    def status(self) -> GateStatus:
        """ Get connection status """
        raise NotImplemented

    @abstractmethod
    def open(self, host: str, port: int, sock: Optional[socket.socket] = None) -> Optional[socket.error]:
        """ Start connection """
        raise NotImplemented

    @abstractmethod
    def close(self):
        """ Close connection """
        raise NotImplemented

    @abstractmethod
    def send(self, payload: bytes, priority: int, delegate: Optional[GateDelegate]):
        """ Send data to remote peer """
        raise NotImplemented
