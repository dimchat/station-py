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
from .starship import StarShip
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

    @property
    def connection(self) -> Connection:
        """ Get current connection """
        raise NotImplemented

    @property
    def worker(self) -> Optional[Worker]:
        """ Get worker for processing packages """
        raise NotImplemented

    @property
    def delegate(self) -> GateDelegate:
        """ Get callback for receiving data """
        yield None

    @property
    def opened(self) -> bool:
        """ Check whether StarGate is not closed and the current Connection is active """
        raise NotImplemented

    @property
    def status(self) -> GateStatus:
        """ Get status """
        raise NotImplemented

    @abstractmethod
    def send_payload(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        """
        Send payload to remote peer

        :param payload:  request data
        :param priority: smaller is the faster, -1 means send it synchronously
        :param delegate: completion handler
        :return: false on error
        """
        raise NotImplemented

    #
    #   Connection
    #

    @abstractmethod
    def send(self, data: bytes) -> bool:
        """
        Send data package

        :param data: package
        :return: false on error
        """
        raise NotImplemented

    @abstractmethod
    def received(self) -> Optional[bytes]:
        """
        Get received data from cache, but not remove

        :return: received data
        """
        raise NotImplemented

    @abstractmethod
    def receive(self, length: int) -> Optional[bytes]:
        """
        Get received data from cache, and remove it
        (call 'received()' to check data first)

        :param length: how many bytes to receive
        :return: received data
        """
        raise NotImplemented

    #
    #   Docking
    #

    @abstractmethod
    def park_ship(self, ship: StarShip) -> bool:
        """ Park this outgo Ship in a waiting queue for departure """
        raise NotImplemented

    # @overload
    # def pop(self) -> Optional[StarShip]:
    #     """ Get a new Ship(time == 0) and remove it from the Dock """
    #     pass
    #
    # @overload
    # def pop(self, sn: bytes) -> Optional[StarShip]:
    #     """ Get a Ship(with SN as ID) and remove it from the Dock """
    #     pass

    @abstractmethod
    def pull_ship(self, sn: Optional[bytes] = None) -> Optional[StarShip]:
        """ Get a parking Ship (remove it from the waiting queue) """
        raise NotImplemented

    @abstractmethod
    def any_ship(self) -> Optional[StarShip]:
        """ Get any Ship timeout/expired (keep it in the waiting queue) """
        raise NotImplemented
