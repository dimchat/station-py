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
from typing import Optional, List, Dict

from .base import Gate, GateStatus, GateDelegate, Ship, StarShip, Worker

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
        self.__fleets: Dict[int, List[StarShip]] = {}
        self.__lock = threading.Lock()

    def put(self, ship: StarShip) -> bool:
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

    # @overload
    # def pop(self) -> Optional[StarShip]:
    #     """ Get a new Ship(time == 0) and remove it from the Dock """
    #     pass
    #
    # @overload
    # def pop(self, sn: bytes) -> Optional[StarShip]:
    #     """ Get a Ship(with SN as ID) and remove it from the Dock """
    #     pass

    def pop(self, sn: Optional[bytes] = None) -> Optional[StarShip]:
        # search in fleets ordered by priority
        with self.__lock:
            if sn is None:
                # get next new ship
                for priority in self.__priorities:
                    fleet = self.__fleets.get(priority, [])
                    for ship in fleet:
                        if ship.time == 0:
                            # update time and try
                            ship.update()
                            fleet.remove(ship)
                            return ship
            else:
                # get ship with ID
                for priority in self.__priorities:
                    fleet = self.__fleets.get(priority, [])
                    for ship in fleet:
                        if ship.sn == sn:
                            fleet.remove(ship)
                            return ship

    def any(self) -> Optional[StarShip]:
        """ Get any Ship timeout/expired """
        with self.__lock:
            expired = int(time.time()) - StarShip.EXPIRES
            for priority in self.__priorities:
                # search in fleets ordered by priority
                fleet = self.__fleets.get(priority, [])
                for ship in fleet:
                    if ship.time > expired:
                        # not expired yet
                        continue
                    if ship.retries <= StarShip.RETRIES:
                        # update time and retry
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
        # time for checking heartbeat
        self.__heartbeat_expired = int(time.time())

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
    def status(self) -> GateStatus:
        return self.gate.status

    def _send_buffer(self, data: bytes) -> bool:
        conn = self.gate.connection
        assert conn is not None, 'Gate connection lost'
        data_len = len(data)
        if self.status == GateStatus.Connected:
            res = conn.send(data=data)
            if res == data_len:
                return True
        # # check connection
        # if conn.socket is None:
        #     raise ConnectionError('Connection lost')
        # try again
        if self.status == GateStatus.Connected:
            res = conn.send(data=data)
            if res == data_len:
                return True

    def _received_buffer(self) -> Optional[bytes]:
        conn = self.gate.connection
        assert conn is not None, 'Gate connection lost'
        buffer = conn.received()
        if buffer is not None:
            return buffer
        # check connection
        if conn.socket is None:
            raise ConnectionError('Connection lost')
        else:
            # try again
            return conn.received()

    def _receive_buffer(self, length: int) -> Optional[bytes]:
        conn = self.gate.connection
        if conn is not None:
            return conn.receive(length=length)

    # Override
    def setup(self):
        pass

    # Override
    def finish(self):
        # TODO: go through all outgo Ships parking in Dock and call 'sent failed' on their delegates
        pass

    # Override
    def handle(self) -> bool:
        # 1. process income
        income = self._get_income_ship()
        if income is not None:
            res = self._handle_ship(income=income)
            if res is not None:
                if res.priority == StarShip.SLOWER:
                    # put the response into waiting queue
                    self.dock.put(ship=res)
                else:
                    # send response directly
                    self._send_ship(outgo=res)
        # 2. process outgo
        outgo = self._get_outgo_ship()
        if outgo is not None:
            if outgo.expired:
                # outgo Ship expired, callback
                delegate = outgo.delegate
                if delegate is not None:
                    delegate.ship_sent(ship=outgo, payload=outgo.payload, error=TimeoutError('Request timeout'))
            elif not self._send_ship(outgo=outgo):
                # failed to send outgo Ship, callback
                delegate = outgo.delegate
                if delegate is not None:
                    delegate.ship_sent(ship=outgo, payload=outgo.payload, error=IOError('Socket error'))
        # 3. heart beat
        if income is None and outgo is None:
            # check time for next heartbeat
            now = time.time()
            if now > self.__heartbeat_expired:
                beat = self._get_heartbeat()
                if beat is not None:
                    # put the heartbeat into waiting queue
                    self.dock.put(ship=beat)
                # try heartbeat next 2 seconds
                self.__heartbeat_expired = now + 2
            return False
        else:
            return True

    @abstractmethod
    def _get_income_ship(self) -> Optional[Ship]:
        """ Get income Ship from Connection """
        raise NotImplemented

    def _handle_ship(self, income: Ship) -> Optional[StarShip]:
        """ Override to process income Ship """
        linked = self._get_outgo_ship(income=income)
        if linked is None:
            return None
        # callback for the linked outgo Ship and remove it
        delegate = linked.delegate
        if delegate is not None:
            delegate.ship_sent(ship=linked, payload=linked.payload)

    def _get_outgo_ship(self, income: Optional[Ship] = None) -> Optional[StarShip]:
        """ Get outgo Ship from waiting queue """
        if income is None:
            # get next new task (time == 0)
            outgo = self.dock.pop()
            if outgo is None:
                # no more new task now, get any expired task
                outgo = self.dock.any()
        else:
            # get task with ID
            outgo = self.dock.pop(sn=income.sn)
        return outgo

    @abstractmethod
    def _send_ship(self, outgo: StarShip) -> bool:
        """ Send outgo Ship via current Connection """
        raise NotImplemented

    def _get_heartbeat(self) -> Optional[StarShip]:
        """ Get an empty ship for keeping connection alive """
        pass
