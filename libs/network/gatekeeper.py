# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
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

"""
    Gate Keeper
    ~~~~~~~~~~~

    for gate in session
"""

import socket
import weakref
from typing import Optional

from startrek.fsm import Runner
from startrek import BaseChannel
from startrek import Connection, ConnectionDelegate, BaseConnection
from startrek import Hub, GateDelegate, ShipDelegate
from tcp import StreamChannel
from tcp import ServerHub as TCPServerHub, ClientHub as TCPClientHub

from dimp import ReliableMessage
from dimsdk import Messenger

from .gate import CommonGate, TCPServerGate, TCPClientGate
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


def reset_send_buffer_size(conn: Connection) -> bool:
    if not isinstance(conn, BaseConnection):
        print('[SOCKET] connection error: %s' % conn)
        return False
    channel = conn.channel
    if not isinstance(channel, BaseChannel):
        print('[SOCKET] channel error: %s, %s' % (channel, conn))
        return False
    sock = channel.sock
    if sock is None:
        print('[SOCKET] socket error: %s, %s' % (sock, conn))
        return False
    size = sock.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
    if size < SEND_BUFFER_SIZE:
        print('[SOCKET] change send buffer size: %d -> %d, %s' % (size, SEND_BUFFER_SIZE, conn))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, SEND_BUFFER_SIZE)
        return True
    else:
        print('[SOCKET] send buffer size: %d, %s' % (size, conn))


SEND_BUFFER_SIZE = 512 * 1024  # 512 KB


class GateKeeper(Runner):

    def __init__(self, address: tuple, sock: Optional[socket.socket], messenger: Messenger, delegate: GateDelegate):
        super().__init__()
        self.__messenger = weakref.ref(messenger)
        self.__remote = address
        self.__gate = self._create_gate(address=address, sock=sock, delegate=delegate)
        # waiting queue
        self.__queue = MessageQueue()
        self.__active = False

    def _create_gate(self, address: tuple, sock: Optional[socket.socket], delegate: GateDelegate) -> CommonGate:
        if sock is None:
            gate = TCPClientGate(delegate=delegate, remote=address)
        else:
            gate = TCPServerGate(delegate=delegate)
        gate.hub = self._create_hub(delegate=gate, address=address, sock=sock)
        return gate

    # noinspection PyMethodMayBeStatic
    def _create_hub(self, delegate: ConnectionDelegate, address: tuple, sock: Optional[socket.socket]) -> Hub:
        if sock is None:
            assert address is not None, 'remote address empty'
            hub = TCPClientHub(delegate=delegate)
            conn = hub.connect(remote=address)
            reset_send_buffer_size(conn=conn)
        else:
            sock.setblocking(False)
            if address is None:
                address = get_remote_address(sock=sock)
            channel = StreamChannel(sock=sock, remote=address, local=get_local_address(sock=sock))
            hub = TCPServerHub(delegate=delegate)
            hub.put_channel(channel=channel)
        return hub

    @property
    def messenger(self) -> Optional[Messenger]:
        return self.__messenger()

    @property
    def remote_address(self) -> tuple:
        return self.__remote

    @property
    def gate(self) -> CommonGate:
        return self.__gate

    @property
    def active(self) -> bool:
        return self.__active

    @active.setter
    def active(self, flag: bool):
        self.__active = flag

    @property  # Override
    def running(self) -> bool:
        if super().running:
            return self.gate.running

    # Override
    def setup(self):
        super().setup()
        self.gate.start()

    # Override
    def finish(self):
        self.gate.stop()
        super().finish()

    # Override
    def process(self) -> bool:
        if self.gate.process():
            # processed income/outgo packages
            return True
        if not self.active:
            # inactive, wait a while to check again
            self.__queue.purge()
            return False
        # get next message
        wrapper = self.__queue.next()
        if wrapper is None:
            # no more task now, purge failed tasks
            self.__queue.purge()
            return False
        # if msg in this wrapper is None (means sent successfully),
        # it must have been cleaned already, so it should not be empty here.
        msg = wrapper.msg
        if msg is None:
            # no more new message
            return True
        # try to push
        data = self.messenger.serialize_message(msg=msg)
        if self.send_payload(payload=data, priority=wrapper.priority, delegate=wrapper):
            wrapper.finished(msg=msg, error=None)
        else:
            wrapper.fail()
        return True

    def send_payload(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        """ Send data via the gate """
        self.gate.send_payload(payload=payload, local=None, remote=self.__remote,
                               priority=priority, delegate=delegate)
        return True

    def push_message(self, msg: ReliableMessage) -> bool:
        """ Push message into a waiting queue """
        return self.__queue.append(msg=msg)
