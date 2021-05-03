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

import threading
import time
import traceback
import weakref
from typing import Optional, List

from tcp import BaseConnection

from dimp import ReliableMessage
from dimsdk import Callback as MessengerCallback

from ..utils import Logging
from ..stargate import GateStatus, GateDelegate, StarGate
from ..stargate import Ship, ShipDelegate

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
    def ship_sent(self, ship, error: Optional[OSError] = None):
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


class MessageQueue:

    def __init__(self):
        super().__init__()
        self.__queue: List[MessageWrapper] = []
        self.__lock = threading.Lock()

    def append(self, msg: ReliableMessage) -> bool:
        with self.__lock:
            wrapper = MessageWrapper(msg=msg)
            self.__queue.append(wrapper)
            return True

    def pop(self) -> Optional[MessageWrapper]:
        with self.__lock:
            if len(self.__queue) > 0:
                return self.__queue.pop(0)

    def next(self) -> Optional[MessageWrapper]:
        """ Get next new message """
        with self.__lock:
            for wrapper in self.__queue:
                if wrapper.virgin:
                    wrapper.mark()  # mark sent
                    return wrapper

    def eject(self) -> Optional[MessageWrapper]:
        """ Get any message sent or failed """
        with self.__lock:
            for wrapper in self.__queue:
                if wrapper.msg is None or wrapper.failed:
                    self.__queue.remove(wrapper)
                    return wrapper


class BaseSession(threading.Thread, GateDelegate, Logging):

    def __init__(self, messenger: CommonMessenger, connection: BaseConnection):
        super().__init__()
        self.__queue = MessageQueue()
        self.__messenger = weakref.ref(messenger)
        self.__connection = connection
        gate = StarGate(connection=connection)
        gate.delegate = self
        connection.delegate = gate
        self.__gate = gate
        # session status
        self.__active = False
        self.__running = False

    def __del__(self):
        # store stranded messages
        self.__flush()

    def __flush(self):
        # store all message
        wrapper = self.__queue.pop()
        while wrapper is not None:
            msg = wrapper.msg
            if msg is not None:
                g_database.store_message(msg=msg)
            wrapper = self.__queue.pop()

    def __clean(self):
        wrapper = self.__queue.eject()
        while wrapper is not None:
            msg = wrapper.msg
            if msg is not None:
                # task failed
                g_database.store_message(msg=msg)
            wrapper = self.__queue.eject()

    @property
    def messenger(self) -> Optional[CommonMessenger]:
        return self.__messenger()

    @property
    def gate(self) -> StarGate:
        return self.__gate

    @property
    def active(self) -> bool:
        return self.__active and self.__gate.opened

    @active.setter
    def active(self, value: bool):
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
        assert isinstance(self.__connection, BaseConnection), 'connection error: %s' % self.__connection
        threading.Thread(target=self.__connection.run).start()
        time.sleep(0.5)
        self.__gate.setup()

    def finish(self):
        assert isinstance(self.__connection, BaseConnection), 'connection error: %s' % self.__connection
        self.__gate.finish()
        self.__connection.stop()
        # save unsent messages
        self.__flush()

    @property
    def running(self) -> bool:
        return self.__running and self.__gate.opened

    def handle(self):
        while self.running:
            if not self.process():
                self._idle()

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.1)

    def process(self) -> bool:
        if self.__gate.process():
            return True
        self.__clean()
        if not self.active:
            # inactive
            return False
        # get next message
        wrapper = self.__queue.next()
        if wrapper is None:
            msg = None
        else:
            msg = wrapper.msg
        if msg is None:
            # no more new message
            return False
        # try to push
        if not self.messenger.send_message(msg=msg, callback=wrapper):
            wrapper.fail()
        return True

    def send(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        if self.active:
            return self.__gate.send_payload(payload=payload, priority=priority, delegate=delegate)

    def push_message(self, msg: ReliableMessage) -> bool:
        """ Push message when session active """
        if self.active:
            return self.__queue.append(msg=msg)

    #
    #   GateDelegate
    #

    def gate_status_changed(self, gate, old_status: GateStatus, new_status: GateStatus):
        if new_status == GateStatus.Connected:
            self.messenger.connected()

    def gate_received(self, gate, ship: Ship) -> Optional[bytes]:
        payload = ship.payload
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
