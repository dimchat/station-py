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
from typing import Optional, List

from dimp import ReliableMessage
from dimsdk import Callback as MessengerCallback

from ..utils import NotificationCenter

from ..network import Connection
from ..network import ShipDelegate
from ..network import Arrival, Departure

from .notification import NotificationNames
from .database import Database
from .database.message_table import is_broadcast_message


g_database = Database()


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
