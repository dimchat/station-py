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
from typing import Optional, List

from dimp import ReliableMessage
from dimsdk import Callback as MessengerCallback

from ..utils import NotificationCenter, Logging

from ..network import Connection, ConnectionDelegate
from ..network import Gate, GateStatus, GateDelegate
from ..network import ShipDelegate
from ..network import Arrival, Departure
from ..network import StreamChannel, ClientHub
from ..network import TCPGate
from ..network import MTPStreamArrival, MarsStreamArrival, WSArrival

from .notification import NotificationNames
from .database import Database
from .messenger import CommonMessenger


g_database = Database()


def is_broadcast_message(msg: ReliableMessage):
    if msg.receiver.is_broadcast:
        return True
    group = msg.group
    return group is not None and group.is_broadcast


class MessageWrapper(ShipDelegate, MessengerCallback):

    EXPIRES = 600  # 10 minutes

    def __init__(self, msg: ReliableMessage):
        super().__init__()
        self.__time = 0
        self.__msg = msg

    @property
    def priority(self) -> int:
        msg = self.__msg
        if msg is not None:
            if is_broadcast_message(msg=msg):
                return 1  # SLOWER
        return 0  # NORMAL

    @property
    def msg(self) -> Optional[ReliableMessage]:
        return self.__msg

    def mark(self):
        self.__time = 1

    def fail(self):
        self.__time = -1

    @property
    def virgin(self) -> bool:
        return self.__time == 0

    @property
    def failed(self) -> bool:
        if self.__time == -1:
            return True
        if self.__time > 1:
            delta = int(time.time()) - self.__time
            return delta > self.EXPIRES

    #
    #   ShipDelegate
    #

    def gate_received(self, ship: Arrival, source: tuple, destination: Optional[tuple], connection: Connection):
        pass

    def gate_sent(self, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        msg = self.__msg
        if isinstance(msg, ReliableMessage):
            NotificationCenter().post(name=NotificationNames.MESSAGE_SENT, sender=self, info=msg.dictionary)
            g_database.erase_message(msg=msg)
        self.__msg = None

    def gate_error(self, error, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        self.__time = -1

    #
    #   Callback
    #
    def finished(self, result, error=None):
        if error is None:
            # this message was assigned to the worker of StarGate,
            # update sent time
            self.__time = int(time.time())
        else:
            # failed
            self.__time = -1


class MessageQueue:

    def __init__(self):
        super().__init__()
        self.__wrappers: List[MessageWrapper] = []
        self.__lock = threading.Lock()

    @property
    def length(self) -> int:
        with self.__lock:
            return len(self.__wrappers)

    def append(self, msg: ReliableMessage) -> bool:
        with self.__lock:
            # check duplicated
            signature = msg.get('signature')
            for wrapper in self.__wrappers:
                item = wrapper.msg
                if item is not None and item.get('signature') == signature:
                    return True
            # append with wrapper
            wrapper = MessageWrapper(msg=msg)
            self.__wrappers.append(wrapper)
            return True

    def pop(self) -> Optional[MessageWrapper]:
        with self.__lock:
            if len(self.__wrappers) > 0:
                return self.__wrappers.pop(0)

    def next(self) -> Optional[MessageWrapper]:
        """ Get next new message """
        with self.__lock:
            for wrapper in self.__wrappers:
                if wrapper.virgin:
                    wrapper.mark()  # mark sent
                    return wrapper

    def eject(self) -> Optional[MessageWrapper]:
        """ Get any message sent or failed """
        with self.__lock:
            for wrapper in self.__wrappers:
                if wrapper.msg is None or wrapper.failed:
                    self.__wrappers.remove(wrapper)
                    return wrapper


def create_hub(delegate: ConnectionDelegate,
               address: Optional[tuple] = None,
               sock: Optional[socket.socket] = None) -> ClientHub:
    """ Create TPC client hub """
    hub = ClientHub(delegate=delegate)
    if sock is None:
        assert address is not None, 'remote address empty'
        hub.connect(remote=address)
    else:
        sock.setblocking(False)
        if address is None:
            address = sock.getpeername()
        channel = StreamChannel(sock=sock, remote=address, local=None)
        hub.put_channel(channel=channel)
    return hub


def create_gate(delegate: GateDelegate,
                address: Optional[tuple] = None,
                sock: Optional[socket.socket] = None) -> TCPGate:
    """ Create TCP gate """
    gate = TCPGate(delegate=delegate)
    gate.hub = create_hub(delegate=gate, address=address, sock=sock)
    return gate


class BaseSession(threading.Thread, GateDelegate, Logging):

    def __init__(self, messenger: CommonMessenger, address: tuple, sock: Optional[socket.socket] = None):
        super().__init__()
        self.__queue = MessageQueue()
        self.__messenger = weakref.ref(messenger)
        self.__gate = create_gate(delegate=self, address=address, sock=sock)
        self.__remote = address
        # session status
        self.__active = False
        self.__running = False

    def __del__(self):
        # store stranded messages
        self.__flush()

    def __flush(self):
        # store all messages
        self.info('saving %d unsent message(s)' % self.__queue.length)
        while True:
            wrapper = self.__queue.pop()
            if wrapper is None:
                break
            msg = wrapper.msg
            if msg is not None:
                g_database.store_message(msg=msg)

    def __clean(self):
        # store expired messages
        while True:
            wrapper = self.__queue.eject()
            if wrapper is None:
                break
            msg = wrapper.msg
            if msg is not None:
                # task failed
                self.warning('clean expired msg: %s -> %s' % (msg.sender, msg.receiver))
                g_database.store_message(msg=msg)

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        return self.__messenger()

    @property
    def gate(self) -> TCPGate:
        return self.__gate

    @property
    def active(self) -> bool:
        return self.__active and self.__gate.running

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
        self.__gate.start()

    def finish(self):
        self.__running = False
        self.__gate.stop()
        self.__flush()

    @property
    def running(self) -> bool:
        return self.__running and self.__gate.running

    def handle(self):
        while self.running:
            if not self.process():
                self._idle()

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.1)

    def process(self) -> bool:
        if self.__gate.process():
            # processed income/outgo packages
            return True
        self.__clean()
        if not self.active:
            # inactive
            return False
        # get next message
        wrapper = self.__queue.next()
        if wrapper is None:
            # no more new message
            msg = None
        else:
            # if msg in this wrapper is None (means sent successfully),
            # it must have been cleaned already, so it should not be empty here.
            msg = wrapper.msg
        if msg is None:
            # no more new message
            return False
        # try to push
        data = self.messenger.serialize_message(msg=msg)
        if self.send_payload(payload=data, priority=wrapper.priority, delegate=wrapper):
            return True
        else:
            wrapper.fail()
            return False

    def send_payload(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        gate = self.gate
        if self.active:
            return gate.send_payload(payload=payload, local=None, remote=self.__remote,
                                     priority=priority, delegate=delegate)
        else:
            self.error('session inactive, cannot send message (%d) now' % len(payload))

    def push_message(self, msg: ReliableMessage) -> bool:
        """ Push message when session active """
        if self.active:
            return self.__queue.append(msg=msg)

    #
    #   GateDelegate
    #

    def gate_status_changed(self, previous: GateStatus, current: GateStatus,
                            remote: tuple, local: Optional[tuple], gate: Gate):
        if current is None or current == GateStatus.ERROR:
            self.active = False
            self.stop()
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
        data = b''
        for pack in packages:
            try:
                res = self.messenger.process_package(data=pack)
                if res is not None and len(res) > 0:
                    data += res + b'\n'
            except Exception as error:
                self.error('parse message failed: %s, %s\n payload: %s' % (error, pack, payload))
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        # station MUST respond something to client request
        if len(data) > 0:
            data = data[:-1]  # remove last '\n'
        self.gate.send_response(payload=data, ship=ship, remote=source, local=destination)

    def gate_sent(self, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        pass

    def gate_error(self, error, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        pass
