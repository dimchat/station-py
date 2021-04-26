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
from abc import abstractmethod
from enum import IntEnum
from typing import Optional

from tcp import Connection, ConnectionStatus, ConnectionHandler


"""
    Star Gate
    ~~~~~~~~~
    
    Connected remote peer
"""


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

    # @abstractmethod
    def gate_received(self, gate, payload: bytes) -> Optional[bytes]:
        """
        Callback when new package received

        :param gate:       remote gate
        :param payload:    received data
        :return response
        """
        pass

    # @abstractmethod
    def gate_sent(self, gate, payload: bytes, error: Optional[OSError] = None):
        """
        Callback when package sent

        :param gate:       remote gate
        :param payload:    request data
        :param error:      None on success
        """
        pass


class Gate(ConnectionHandler):
    """ Star Gate of remote peer """

    # flow control
    MAX_INCOMES_PER_OUTGO = 4
    # seconds
    INCOME_INTERVAL = 8.0 / 1000.0
    OUTGO_INTERVAL = 32.0 / 1000.0
    IDLE_INTERVAL = 256.0 / 1000.0

    @property
    def status(self) -> GateStatus:
        """ Get connection status """
        raise NotImplemented

    @property
    def delegate(self) -> Optional[GateDelegate]:
        """ Get default Delegate """
        yield None

    @property
    def connection(self) -> Optional[Connection]:
        """ Get current Connection """
        yield None

    @abstractmethod
    def open(self, address: Optional[tuple] = None, sock: Optional[socket.socket] = None) -> Optional[Connection]:
        """ Start connection """
        raise NotImplemented

    @abstractmethod
    def close(self):
        """ Close connection """
        raise NotImplemented

    @abstractmethod
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[GateDelegate] = None) -> bool:
        """ Send data to remote peer """
        raise NotImplemented

    @abstractmethod
    def process(self):
        raise NotImplemented


"""
    Star Ship
    ~~~~~~~~~
    
    Container carrying data package
"""


class Ship:
    """ Star Ship for carrying data """

    @property
    def sn(self) -> bytes:
        """ Get ID for this Ship """
        raise NotImplemented

    @property
    def payload(self) -> bytes:
        """ Get data in this Ship """
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

    @property
    def expired(self) -> bool:
        """ Check whether retry too many times and no response """
        delta = int(time.time()) - self.time
        return delta > (self.EXPIRES * self.RETRIES * 2)

    def update(self):
        """ Update retries count and time """
        raise NotImplemented


"""
    Star Worker
    ~~~~~~~~~~~
    
    Processor for Star Ships
"""


class Worker:
    """ Star Worker for packages in Ships """

    @abstractmethod
    def setup(self):
        """ Set up connection """
        raise NotImplemented

    @abstractmethod
    def handle(self) -> bool:
        """ Process incoming/outgoing Ships """
        raise NotImplemented

    @abstractmethod
    def finish(self):
        """ Do clean jobs """
        raise NotImplemented

    @abstractmethod
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[GateDelegate] = None) -> bool:
        """ Send data to remote peer """
        raise NotImplemented
