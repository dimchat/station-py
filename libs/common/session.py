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
import traceback
from abc import ABC
from threading import Thread
from typing import Optional

from startrek.fsm import Runner
from startrek import Connection, BaseConnection
from startrek import GateDelegate
from startrek import Arrival, Departure, DepartureShip

from dimp import ID, ReliableMessage
from dimsdk import Messenger

from ..utils import Logging

from ..network import ShipDelegate, CommonGate, GateKeeper
from ..network import WSArrival, MarsStreamArrival, MTPStreamArrival


class BaseSession(Runner, GateDelegate, Logging, ABC):

    def __init__(self, messenger: Messenger, address: tuple, sock: Optional[socket.socket] = None):
        super().__init__()
        self.__keeper = self._create_gate_keeper(messenger=messenger, address=address, sock=sock)
        self.__thread: Optional[Thread] = None
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

    @property
    def key(self) -> Optional[str]:
        """ session key """
        raise NotImplemented

    def __str__(self):
        clazz = self.__class__.__name__
        return '<%s:%s %s|%s active=%s />' % (clazz, self.key, self.remote_address, self.identifier, self.active)

    def __repr__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s:%s %s|%s active=%s />' % (clazz, self.key, self.remote_address, self.identifier, self.active)

    def start(self):
        self.__force_stop()
        t = Thread(target=self.run)
        self.__thread = t
        t.start()

    def __force_stop(self):
        keeper = self.keeper
        if keeper.running:
            keeper.stop()
        t: Thread = self.__thread
        if t is not None:
            # waiting 2 seconds for stopping the thread
            self.__thread = None
            t.join(timeout=2.0)

    @property  # Override
    def running(self) -> bool:
        if super().running:
            return self.keeper.running

    # Override
    def stop(self):
        self.__force_stop()
        super().stop()

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
    #   Send message to remote address
    #

    def send_payload(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        return self.keeper.send_payload(payload=payload, priority=priority, delegate=delegate)

    def push_message(self, msg: ReliableMessage) -> bool:
        return self.keeper.push_message(msg=msg)

    #
    #   GateDelegate
    #

    # Override
    def gate_received(self, ship: Arrival,
                      source: tuple, destination: Optional[tuple], connection: Connection):
        if isinstance(ship, MTPStreamArrival):
            payload = ship.payload
        elif isinstance(ship, MarsStreamArrival):
            payload = ship.payload
        elif isinstance(ship, WSArrival):
            payload = ship.payload
        else:
            raise ValueError('unknown arrival ship: %s' % ship)
        # check payload
        if payload.startswith(b'{'):
            # JsON in lines
            packages = payload.splitlines()
        else:
            packages = [payload]
        array = []
        messenger = self.messenger
        for pack in packages:
            try:
                responses = messenger.process_package(data=pack)
                for res in responses:
                    if res is None or len(res) == 0:
                        # should not happen
                        continue
                    array.append(res)
            except Exception as error:
                self.error('parse message failed (%s): %s, %s' % (source, error, pack))
                self.error('payload: %s' % payload)
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        gate = self.gate
        if len(array) == 0:
            if isinstance(connection, BaseConnection) and not connection.is_activated:
                # station MUST respond something to client request (Tencent Mars)
                gate.send_response(payload=b'', ship=ship, remote=source, local=destination)
        else:
            for item in array:
                gate.send_response(payload=item, ship=ship, remote=source, local=destination)

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
