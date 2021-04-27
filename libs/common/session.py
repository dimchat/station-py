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

from tcp import Connection

from dimp import ReliableMessage
from dimsdk import Callback as MessengerCallback

from ..utils import Logging
from ..stargate import GateStatus, GateDelegate, StarGate, ShipDelegate

from .database import Database
from .messenger import CommonMessenger


g_database = Database()


class MessageWrapper(ShipDelegate, MessengerCallback):

    EXPIRES = 600  # 10 minutes

    def __init__(self, msg: ReliableMessage):
        super().__init__()
        self.__time = 0
        self.__msg = msg

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
    def ship_sent(self, ship, payload: bytes, error: Optional[OSError] = None):
        if error is None:
            # success, remove message
            self.__msg = None
        else:
            # failed
            self.__time = -1

    #
    #   Callback
    #
    def finished(self, result, error=None):
        if error is None:
            # this message was assigned to the Worker of StarGate,
            # update sent time
            self.__time = int(time.time())
        else:
            # failed
            self.__time = -1


class BaseSession(threading.Thread, GateDelegate, Logging):

    def __init__(self, messenger: CommonMessenger,
                 address: Optional[tuple] = None,
                 sock: Optional[socket.socket] = None):
        super().__init__()
        self.__messenger = weakref.ref(messenger)
        self.__gate = StarGate(address=address, sock=sock)
        self.__gate.delegate = self
        # session status
        self.__active = False
        self.__running = False
        # message queue
        self.__queue: List[MessageWrapper] = []
        self.__lock = threading.Lock()

    def __del__(self):
        # store stranded messages
        self.__flush()

    def __flush(self):
        # store all message
        wrapper = self.__pop()
        while wrapper is not None:
            msg = wrapper.msg
            if msg is not None:
                g_database.store_message(msg=msg)
            wrapper = self.__pop()

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        return self.__messenger()

    @property
    def gate(self) -> StarGate:
        return self.__gate

    @property
    def connection(self) -> Connection:
        return self.gate.connection

    @property
    def active(self) -> bool:
        return self.__active

    @active.setter
    def active(self, value: bool):
        self.__active = value

    def stop(self):
        self.__running = False

    def setup(self):
        pass

    def handle(self) -> bool:
        pass

    def finish(self):
        pass

    def run(self):
        self.setup()
        self.__running = True
        while self.__running:
            self.__clean()
            if not self.__active:
                # inactive
                if not self.handle():
                    # have a rest ^_^
                    time.sleep(0.1)
                continue
            # get next message
            wrapper = self.__next()
            if wrapper is None:
                msg = None
            else:
                msg = wrapper.msg
            if msg is None:
                # no more new message
                if not self.handle():
                    # have a rest ^_^
                    time.sleep(0.1)
                continue
            # try to push
            if not self.messenger.send_message(msg=msg, callback=wrapper):
                wrapper.fail()
        self.finish()
        # save unsent messages
        self.__flush()

    def send(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        if self.__active:
            return self.__gate.send(payload=payload, priority=priority, delegate=delegate)

    def push_message(self, msg: ReliableMessage) -> bool:
        """ Push message when session active """
        with self.__lock:
            if self.__active:
                wrapper = MessageWrapper(msg=msg)
                self.__queue.append(wrapper)
                return True

    def __pop(self) -> Optional[MessageWrapper]:
        with self.__lock:
            if len(self.__queue) > 0:
                return self.__queue.pop(0)

    def __next(self) -> Optional[MessageWrapper]:
        with self.__lock:
            for wrapper in self.__queue:
                if wrapper.virgin:
                    wrapper.mark()  # mark sent
                    return wrapper

    def __eject(self) -> Optional[MessageWrapper]:
        with self.__lock:
            for wrapper in self.__queue:
                if wrapper.msg is None or wrapper.failed:
                    self.__queue.remove(wrapper)
                    return wrapper

    def __clean(self):
        wrapper = self.__eject()
        while wrapper is not None:
            msg = wrapper.msg
            if msg is not None:
                # task failed
                g_database.store_message(msg=msg)
            wrapper = self.__eject()

    #
    #   GateDelegate
    #

    def gate_status_changed(self, gate, old_status: GateStatus, new_status: GateStatus):
        if new_status == GateStatus.Connected:
            self.messenger.connected()

    def gate_received(self, gate, payload: bytes) -> Optional[bytes]:
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
                self.error('parse message failed: %s, %s' % (error, pack))
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        # station MUST respond something to client request
        if len(data) > 0:
            data = data[:-1]  # remove last '\n'
        return data
