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
    Message Queue
    ~~~~~~~~~~~~~

    for session server
"""

import threading
import time
from typing import Optional, List, Dict, Union

from startrek import Connection
from startrek import ShipDelegate
from startrek import Arrival, Departure, DeparturePriority

from dimp import ReliableMessage

from ..utils import get_msg_sig

from ..database import Database


g_database = Database()


class MessageWrapper(ShipDelegate):

    EXPIRES = 600  # 10 minutes

    def __init__(self, msg: ReliableMessage, priority: int):
        super().__init__()
        self.__time = 0
        self.__msg = msg
        self.__priority = priority

    @property
    def priority(self) -> int:
        return self.__priority

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

    def is_failed(self, now: int) -> bool:
        if self.__time == -1:
            return True
        if self.__time > 1:
            expired = self.__time + self.EXPIRES
            return now > expired

    def success(self):
        # this message was assigned to the worker of StarGate,
        # update sent time
        self.__time = int(time.time())

    # noinspection PyUnusedLocal
    def failed(self, error: Exception):
        # gate error, failed to append
        self.__time = -1

    #
    #   ShipDelegate
    #

    # Override
    def gate_received(self, ship: Arrival, source: tuple, destination: Optional[tuple], connection: Connection):
        pass

    # Override
    def gate_sent(self, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        msg = self.__msg
        self.__msg = None
        if isinstance(msg, ReliableMessage):
            sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
            print('[QUEUE] message sent, remove from db: %s, %s -> %s' % (sig, msg.sender, msg.receiver))
            g_database.remove_message(msg=msg)

    # Override
    def gate_error(self, error: IOError, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        self.__time = -1


class MessageQueue:

    def __init__(self):
        super().__init__()
        self.__priorities: List[int] = []
        self.__fleets: Dict[int, List[MessageWrapper]] = {}  # priority => List[MessageWrapper]
        self.__lock = threading.Lock()

    def append(self, msg: ReliableMessage, priority: Union[int, DeparturePriority]) -> bool:
        if isinstance(priority, DeparturePriority):
            priority = priority.value
        with self.__lock:
            # 1. choose an array with priority
            fleet = self.__fleets.get(priority)
            if fleet is None:
                # 1.1. create new array for this priority
                fleet = []
                self.__fleets[priority] = fleet
                # 1.2. insert the priority in a sorted list
                self.__insert(priority=priority)
            else:
                # 1.3. check duplicated
                signature = msg.get('signature')
                for wrapper in fleet:
                    item = wrapper.msg
                    if item is not None and item.get('signature') == signature:
                        print('[QUEUE] duplicated message: %s' % signature)
                        return True
            # 2. append with wrapper
            wrapper = MessageWrapper(msg=msg, priority=priority)
            fleet.append(wrapper)
            return True

    def __insert(self, priority: int) -> bool:
        index = 0
        for value in self.__priorities:
            if value == priority:
                # duplicated
                return False
            elif value > priority:
                # got it
                break
            else:
                # current value is smaller than the new value,
                # keep going
                index += 1
        # insert new value before the bigger one
        self.__priorities.insert(index, priority)
        return True

    def next(self) -> Optional[MessageWrapper]:
        """ Get next new message """
        with self.__lock:
            for priority in self.__priorities:
                # 1. get messages with priority
                fleet = self.__fleets.get(priority)
                if fleet is None:
                    continue
                # 2. seeking new task in this priority
                for wrapper in fleet:
                    if wrapper.virgin:
                        wrapper.mark()  # got it, mark sent
                        return wrapper

    def __eject(self, now: int) -> Optional[MessageWrapper]:
        """ Get any message sent or failed """
        with self.__lock:
            for priority in self.__priorities:
                # 1. get messages with priority
                fleet = self.__fleets.get(priority)
                if fleet is None:
                    continue
                for wrapper in fleet:
                    if wrapper.msg is None or wrapper.is_failed(now=now):
                        fleet.remove(wrapper)  # got it, remove from the queue
                        return wrapper

    def purge(self) -> int:
        count = 0
        now = int(time.time())
        wrapper = self.__eject(now=now)
        while wrapper is not None:
            count += 1
            # TODO: callback for failed task?
            wrapper = self.__eject(now=now)
        return count
