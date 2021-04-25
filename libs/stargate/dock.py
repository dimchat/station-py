# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
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

import threading
import time
import weakref
from abc import abstractmethod
from typing import Optional, List, Dict, overload

from tcp import Connection

from .base import Gate, GateDelegate, OutgoShip, Worker

"""
    Star Dock
    ~~~~~~~~~

    Parking Star Ships
"""


class Dock:

    def __init__(self):
        super().__init__()
        # tasks for sending out
        self.__priorities: List[int] = []
        self.__fleets: Dict[int, List[OutgoShip]] = {}
        self.__lock = threading.Lock()

    def put(self, ship: OutgoShip) -> bool:
        """ Park this ship in the Dock for departure """
        with self.__lock:
            # 1. choose an array with priority
            priority = ship.priority
            fleet = self.__fleets.get(priority)
            if fleet is None:
                # 1.1. create new array for this priority
                fleet = []
                self.__fleets[priority] = fleet
                # 1.2. insert the priority in a sorted list
                index = 0
                count = len(self.__priorities)
                while index < count:
                    if priority < self.__priorities[index]:
                        # insert priority before the bigger one
                        break
                    else:
                        index += 1
                self.__priorities.insert(index, priority)
            # 2. check duplicated task
            for item in fleet:
                if item is ship:
                    return False
            # 3. append to the tail
            fleet.append(ship)
            return True

    @overload
    def pop(self) -> Optional[OutgoShip]:
        """ Get a new Ship(time == 0) and remove it from the Dock """
        pass

    @overload
    def pop(self, sn: bytes) -> Optional[OutgoShip]:
        """ Get a Ship(with SN as ID) and remove it from the Dock """
        pass

    def pop(self, sn: Optional[bytes] = None) -> Optional[OutgoShip]:
        # search in fleets ordered by priority
        with self.__lock:
            if sn is None:
                # get next new ship
                for priority in self.__priorities:
                    fleet = self.__fleets.get(priority, [])
                    for ship in fleet:
                        if ship.time == 0:
                            # got it
                            fleet.remove(ship)
                            return ship
            else:
                # get ship with ID
                for priority in self.__priorities:
                    fleet = self.__fleets.get(priority, [])
                    for ship in fleet:
                        if ship.sn == sn:
                            # got it
                            fleet.remove(ship)
                            return ship

    def any(self) -> Optional[OutgoShip]:
        """ Get any Ship timeout/expired """
        with self.__lock:
            expired = int(time.time()) - OutgoShip.EXPIRES
            for priority in self.__priorities:
                # search in fleets ordered by priority
                fleet = self.__fleets.get(priority, [])
                for ship in fleet:
                    if ship.time > expired:
                        # not expired yet
                        continue
                    if ship.retries < OutgoShip.RETRIES:
                        # got it, update time and retry
                        ship.update()
                        return ship
                    # retried too many times
                    if ship.expired:
                        # task expired, remove it and don't retry
                        fleet.remove(ship)
                        return ship


class Docker(Worker):

    def __init__(self, gate: Gate):
        super().__init__()
        self.__dock = Dock()
        self.__gate = weakref.ref(gate)
        self.__counter = 0

    @property
    def dock(self) -> Dock:
        return self.__dock

    @property
    def gate(self) -> Gate:
        return self.__gate()

    @property
    def delegate(self) -> Optional[GateDelegate]:
        return self.gate.delegate

    @property
    def connection(self) -> Optional[Connection]:
        return self.gate.connection

    # Override
    def setup(self):
        pass

    # Override
    def finish(self):
        # TODO: go through all outgo Ships parking in Dock and call 'sent failed' on their delegates
        pass

    # Override
    def handle(self):
        # process incoming packages / outgoing tasks
        if Gate.MAX_INCOMES_PER_OUTGO > 0:
            # incoming priority
            if self.__counter < Gate.MAX_INCOMES_PER_OUTGO:
                if self._handle_income():
                    self.__counter += 1
                    return
            # keep a chance for outgoing packages
            if self._handle_outgo():
                self.__counter = 0
                return
        else:
            # outgoing priority
            assert Gate.MAX_INCOMES_PER_OUTGO != 0, 'cannot set MAX_INCOMES_PER_OUTGO to 0'
            if self.__counter > Gate.MAX_INCOMES_PER_OUTGO:
                if self._handle_outgo():
                    self.__counter -= 1
                    return
            # keep a chance for incoming packages
            if self._handle_income():
                self.__counter = 0
                return
        # no task now, send a HEARTBEAT package
        self._handle_heartbeat()
        self.__counter = 0
        return

    @abstractmethod
    def _handle_income(self) -> bool:
        raise NotImplemented

    @abstractmethod
    def _handle_outgo(self) -> bool:
        raise NotImplemented

    def _handle_heartbeat(self) -> bool:
        pass
