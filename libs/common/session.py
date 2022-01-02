# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

"""
    Session Server
    ~~~~~~~~~~~~~~

    for login user
"""

import socket
from abc import ABC
from typing import Optional

from startrek.fsm import Runner
from startrek import Connection
from startrek import GateDelegate
from startrek import Departure, DepartureShip

from dimp import ID, Content
from dimp import InstantMessage, ReliableMessage
from dimsdk import Messenger, Transmitter

from ..utils import Logging

from ..network import CommonGate, GateKeeper


class BaseSession(Runner, Transmitter, GateDelegate, Logging, ABC):

    def __init__(self, messenger: Messenger, address: tuple, sock: Optional[socket.socket] = None):
        super().__init__()
        self.__keeper = self._create_gate_keeper(messenger=messenger, address=address, sock=sock)
        self.__identifier: Optional[ID] = None

    def _create_gate_keeper(self, address: tuple, sock: Optional[socket.socket], messenger: Messenger):
        return GateKeeper(address=address, sock=sock, messenger=messenger, delegate=self)

    @property
    def identifier(self) -> Optional[ID]:
        return self.__identifier

    @identifier.setter
    def identifier(self, value: ID):
        self.__identifier = value

    @property
    def keeper(self) -> GateKeeper:
        return self.__keeper

    @property
    def messenger(self) -> Optional[Messenger]:
        return self.keeper.messenger

    @property
    def remote_address(self) -> tuple:
        return self.keeper.remote_address

    @property
    def gate(self) -> CommonGate:
        return self.keeper.gate

    @property
    def active(self) -> bool:
        return self.keeper.active

    @active.setter
    def active(self, flag: bool):
        self.keeper.active = flag

    # Override
    def stop(self):
        super().stop()
        self.keeper.stop()

    @property
    def key(self) -> Optional[str]:
        """ session key """
        raise NotImplemented

    def __str__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s:%s %s|%s active=%s />' % (clazz, self.key, self.remote_address, self.identifier, self.active)

    def __repr__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s:%s %s|%s active=%s />' % (clazz, self.key, self.remote_address, self.identifier, self.active)

    @property  # Override
    def running(self) -> bool:
        if super().running:
            return self.keeper.running

    # Override
    def setup(self):
        super().setup()
        self.keeper.setup()

    # Override
    def finish(self):
        self.keeper.finish()
        super().finish()

    # Override
    def process(self) -> bool:
        return self.keeper.process()

    #
    #   Transmitter
    #

    # Override
    def send_reliable_message(self, msg: ReliableMessage, priority: int) -> bool:
        if not self.active:
            # FIXME: connection lost?
            self.warning(msg='session inactive')
        self.debug(msg='sending reliable message to: %s, priority: %d' % (msg.receiver, priority))
        return self.keeper.send_reliable_message(msg=msg, priority=priority)

    # Override
    def send_instant_message(self, msg: InstantMessage, priority: int) -> bool:
        if not self.active:
            # FIXME: connection lost?
            self.warning(msg='session inactive')
        self.debug(msg='sending instant message to: %s, priority: %d' % (msg.receiver, priority))
        return self.keeper.send_instant_message(msg=msg, priority=priority)

    # Override
    def send_content(self, sender: Optional[ID], receiver: ID, content: Content, priority: int) -> bool:
        if not self.active:
            # FIXME: connection lost?
            self.warning(msg='session inactive')
        self.debug(msg='sending content to: %s, priority: %d' % (receiver, priority))
        return self.keeper.send_content(sender=sender, receiver=receiver, content=content, priority=priority)

    #
    #   GateDelegate
    #

    # Override
    def gate_sent(self, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        delegate = None
        if isinstance(ship, DepartureShip):
            delegate = ship.delegate
        # callback to MessageWrapper
        if delegate is not None and delegate != self:
            delegate.gate_sent(ship=ship, source=source, destination=destination, connection=connection)

    # Override
    def gate_error(self, error, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        delegate = None
        if isinstance(ship, DepartureShip):
            delegate = ship.delegate
        # callback to MessageWrapper
        if delegate is not None and delegate != self:
            delegate.gate_error(error=error, ship=ship, source=source, destination=destination, connection=connection)
