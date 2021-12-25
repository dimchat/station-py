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
from typing import Optional, Set, Union

from startrek.fsm import Runner
from startrek.net.channel import get_remote_address, get_local_address
from startrek import Channel, BaseChannel
from startrek import Connection, ConnectionDelegate, BaseConnection
from startrek import Hub, GateDelegate, ShipDelegate
from startrek import DeparturePriority
from tcp import StreamChannel
from tcp import ServerHub as TCPServerHub, ClientHub

from dimp import ID, Envelope, Content
from dimp import InstantMessage, ReliableMessage
from dimsdk import Messenger

from ..utils import Logging

from .gate import CommonGate, TCPServerGate, TCPClientGate
from .queue import MessageQueue


class ServerHub(TCPServerHub, Logging):

    # Override
    def _cleanup_channels(self, channels: Set[Channel]):
        # super()._cleanup_channels(channels=channels)
        closed_channels = set()
        # 1. check closed channels
        for sock in channels:
            if not sock.opened:
                closed_channels.add(sock)
        # 2. remove closed channels
        for sock in closed_channels:
            self.warning(msg='socket channel closed, remove it: %s' % sock)
            self.close_channel(channel=sock)

    # Override
    def _cleanup_connections(self, connections: Set[Connection]):
        # super()._cleanup_connections(connections=connections)
        closed_connections = set()
        # 1. check closed connections
        for conn in connections:
            if not conn.opened:
                closed_connections.add(conn)
        # 2. remove closed connections
        for conn in closed_connections:
            remote = conn.remote_address
            local = conn.local_address
            self.warning(msg='connection closed, remove it: %s' % conn)
            self.disconnect(remote=remote, local=local, connection=conn)


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
            hub = ClientHub(delegate=delegate)
            conn = hub.connect(remote=address)
            reset_send_buffer_size(conn=conn)
        else:
            sock.setblocking(False)
            # sock.settimeout(0.5)
            if address is None:
                address = get_remote_address(sock=sock)
            channel = StreamChannel(sock=sock, remote=address, local=get_local_address(sock=sock))
            hub = ServerHub(delegate=delegate)
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
        gate = self.gate
        hub = gate.hub
        # from tcp import Hub
        # assert isinstance(hub, Hub), 'hub error: %s' % hub
        incoming = hub.process()
        outgoing = gate.process()
        if incoming or outgoing:
            # processed income/outgo packages
            return True
        # if not self.active:
        #     # inactive, wait a while to check again
        #     self.__queue.purge()
        #     return False
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
            # msg sent?
            return True
        # try to push
        data = self.messenger.serialize_message(msg=msg)
        ok = self.__send_payload(payload=data, priority=wrapper.priority, delegate=wrapper)
        if ok:
            wrapper.success()
        else:
            error = IOError('gate error, failed to send data')
            wrapper.failed(error=error)
        return True

    def __send_payload(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        """ Send data via the gate """
        gate = self.gate
        return gate.send_payload(payload=payload, local=None, remote=self.__remote,
                                 priority=priority, delegate=delegate)

    def send_reliable_message(self, msg: ReliableMessage, priority: Union[int, DeparturePriority]) -> bool:
        """ Push message into a waiting queue """
        return self.__queue.append(msg=msg, priority=priority)

    def send_instant_message(self, msg: InstantMessage, priority: Union[int, DeparturePriority]) -> bool:
        """ Push message into q waiting queue after encrypted and signed """
        messenger = self.messenger
        # send message (secured + certified) to target station
        s_msg = messenger.encrypt_message(msg=msg)
        if s_msg is None:
            # public key not found?
            return False
        r_msg = messenger.sign_message(msg=s_msg)
        if r_msg is None:
            # TODO: set msg.state = error
            raise AssertionError('failed to sign message: %s' % s_msg)
        self.send_reliable_message(msg=r_msg, priority=priority)
        # TODO: if OK, set msg.state = sending; else set msg.state = waiting
        # save signature for receipt
        msg['signature'] = r_msg.get('signature')
        from ..common import CommonMessenger
        assert isinstance(messenger, CommonMessenger), 'messenger error: %s' % messenger
        return messenger.save_message(msg=msg)

    def send_content(self, content: Content, priority: Union[int, DeparturePriority], receiver: ID, sender: ID = None):
        """ Send message content with priority """
        # Application Layer should make sure user is already login before it send message to server.
        # Application layer should put message into queue so that it will send automatically after user login
        if sender is None:
            user = self.messenger.facebook.current_user
            assert user is not None, 'current user not set'
            sender = user.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        msg = InstantMessage.create(head=env, body=content)
        return self.send_instant_message(msg=msg, priority=priority)
