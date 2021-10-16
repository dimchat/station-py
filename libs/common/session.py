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
import threading
import time
import traceback
import weakref
from typing import Optional

from dimp import ReliableMessage

from ..utils import Logging
from ..database import Database

from ..network import Connection, ConnectionDelegate
from ..network import Gate, GateStatus, GateDelegate
from ..network import ShipDelegate
from ..network import Arrival, Departure, DepartureShip
from ..network import StreamChannel
from ..network import Hub, TCPServerHub, TCPClientHub
from ..network import CommonGate, TCPServerGate, TCPClientGate
from ..network import MTPStreamArrival, MarsStreamArrival, WSArrival

from .messenger import CommonMessenger
from .queue import MessageQueue


def get_remote_address(sock: socket.socket) -> Optional[tuple]:
    try:
        return sock.getpeername()
    except socket.error as error:
        print('[SOCKET] failed to get remote address from socket %s: %s' % (sock, error))


def get_local_address(sock: socket.socket) -> Optional[tuple]:
    try:
        return sock.getsockname()
    except socket.error as error:
        print('[SOCKET] failed to get local address from socket %s: %s' % (sock, error))


g_database = Database()


class BaseSession(threading.Thread, GateDelegate, Logging):

    def __init__(self, messenger: CommonMessenger, address: tuple, sock: Optional[socket.socket] = None):
        super().__init__()
        self.__queue = MessageQueue()
        self.__messenger = weakref.ref(messenger)
        self.__gate = self._create_gate(address=address, sock=sock)
        self.__remote = address
        # session status
        self.__active = False
        self.__running = False

    def _create_gate(self, address: tuple, sock: Optional[socket.socket]) -> CommonGate:
        if sock is None:
            gate = TCPClientGate(delegate=self)
        else:
            gate = TCPServerGate(delegate=self)
        gate.hub = self._create_hub(delegate=gate, address=address, sock=sock)
        return gate

    # noinspection PyMethodMayBeStatic
    def _create_hub(self, delegate: ConnectionDelegate, address: tuple, sock: Optional[socket.socket]) -> Hub:
        if sock is None:
            assert address is not None, 'remote address empty'
            hub = TCPClientHub(delegate=delegate)
            hub.connect(remote=address)
        else:
            sock.setblocking(False)
            if address is None:
                address = get_remote_address(sock=sock)
            channel = StreamChannel(sock=sock, remote=address, local=get_local_address(sock=sock))
            hub = TCPServerHub(delegate=delegate)
            hub.put_channel(channel=channel)
        return hub

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        return self.__messenger()

    @property
    def gate(self) -> CommonGate:
        return self.__gate

    @property
    def active(self) -> bool:
        return self.__active and self.gate.running

    @active.setter
    def active(self, value: bool):
        self.__active = value

    def _set_active(self, value: bool):
        self.__active = value

    def run(self):
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def stop(self):
        self.__running = False

    def setup(self):
        self.__running = True
        self.gate.start()

    def finish(self):
        self.gate.stop()
        self.__running = False

    @property
    def running(self) -> bool:
        return self.__running and self.gate.running

    def handle(self):
        while self.running:
            if not self.process():
                self._idle()

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.25)

    def process(self) -> bool:
        if self.gate.process():
            # processed income/outgo packages
            return True
        if not self.active:
            # inactive
            return False
        # get next message
        wrapper = self.__queue.next()
        if wrapper is None:
            # no more new message
            return False
        # if msg in this wrapper is None (means sent successfully),
        # it must have been cleaned already, so it should not be empty here.
        msg = wrapper.msg
        if msg is None:
            # no more new message
            return True
        # try to push
        data = self.messenger.serialize_message(msg=msg)
        if not self.send_payload(payload=data, priority=wrapper.priority, delegate=wrapper):
            wrapper.fail()
        return True

    def send_payload(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        if self.active:
            self.gate.send_payload(payload=payload, local=None, remote=self.__remote,
                                   priority=priority, delegate=delegate)
            return True
        else:
            self.error('session inactive, cannot send message (%d) now' % len(payload))

    def push_message(self, msg: ReliableMessage) -> bool:
        """ Push message when session active """
        if self.active:
            return self.__queue.append(msg=msg)
        else:
            self.error('session inactive, cannot push msg now: %s -> %s' % (msg.sender, msg.receiver))

    #
    #   GateDelegate
    #

    def gate_status_changed(self, previous: GateStatus, current: GateStatus,
                            remote: tuple, local: Optional[tuple], gate: Gate):
        if current is None or current == GateStatus.ERROR:
            self.active = False
            # self.stop()
        elif current == GateStatus.READY:
            self.messenger.connected()

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
                self.error('parse message failed: %s, %s\n payload: %s' % (error, pack, payload))
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        gate = self.gate
        if len(array) == 0:
            # station MUST respond something to client request
            gate.send_response(payload=b'', ship=ship, remote=source, local=destination)
            return False
        for item in array:
            gate.send_response(payload=item, ship=ship, remote=source, local=destination)
        return True

    def gate_sent(self, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        delegate = None
        if isinstance(ship, DepartureShip):
            delegate = ship.delegate
        # callback to MessageWrapper
        if delegate is not None and delegate != self:
            delegate.gate_sent(ship=ship, source=source, destination=destination, connection=connection)

    def gate_error(self, error, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        delegate = None
        if isinstance(ship, DepartureShip):
            delegate = ship.delegate
        # callback to MessageWrapper
        if delegate is not None and delegate != self:
            delegate.gate_error(error=error, ship=ship, source=source, destination=destination, connection=connection)
