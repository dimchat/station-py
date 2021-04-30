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

from abc import abstractmethod
from enum import IntEnum
from typing import Optional

from tcp import Connection, ConnectionStatus

from .ship import Ship, ShipDelegate
from .dock import Dock
from .worker import Worker


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
    if status in [ConnectionStatus.Connected, ConnectionStatus.Maintaining, ConnectionStatus.Expired]:
        return GateStatus.Connected
    if status == ConnectionStatus.Connecting:
        return GateStatus.Connecting
    if status == ConnectionStatus.Error:
        return GateStatus.Error
    # Default
    return GateStatus.Init


class GateDelegate:
    """ Star Gate Delegate """

    @abstractmethod
    def gate_status_changed(self, gate, old_status: GateStatus, new_status: GateStatus):
        """
        Callback when connection status changed

        :param gate:       remote gate
        :param old_status: last status
        :param new_status: current status
        """
        raise NotImplemented

    @abstractmethod
    def gate_received(self, gate, ship: Ship) -> Optional[bytes]:
        """
        Callback when new package received

        :param gate:       remote gate
        :param ship:       data package container
        :return response
        """
        raise NotImplemented


class Gate:
    """ Star Gate of remote peer """

    @abstractmethod
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        """ Send data to remote peer """
        raise NotImplemented

    @property
    def delegate(self) -> GateDelegate:
        """ Get callback """
        yield None

    @property
    def worker(self) -> Optional[Worker]:
        """ Get worker for processing packages """
        raise NotImplemented

    @property
    def dock(self) -> Dock:
        """ Get ship park """
        raise NotImplemented

    @property
    def connection(self) -> Connection:
        """ Get current connection """
        raise NotImplemented

    @property
    def status(self) -> GateStatus:
        """ Get connection status """
        raise NotImplemented
