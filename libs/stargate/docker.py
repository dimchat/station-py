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

import socket
import threading
import time
import traceback
import weakref
from abc import abstractmethod
from typing import Optional, List, Dict, Set

from tcp import Connection, ConnectionStatus

from .base import Gate, GateDelegate
from .base import OutgoShip, Worker


class Dock:

    def __init__(self):
        super().__init__()
        # tasks for sending out
        self.__priorities: List[int] = []
        self.__ships: Dict[int, List[OutgoShip]] = {}
        self.__lock = threading.Lock()

    def push(self, ship: OutgoShip):
        with self.__lock:
            priority = ship.priority
            table = self.__ships.get(priority)
            if table is None:
                # create new table for this priority
                table = []
                self.__ships[priority] = table
                # insert the priority in a sorted list
                index = 0
                count = len(self.__priorities)
                while index < count:
                    if priority < self.__priorities[index]:
                        # insert priority before the bigger one
                        break
                    else:
                        index += 1
                self.__priorities.insert(index, priority)
            # append to tail
            table.append(ship)

    def pop(self) -> Optional[OutgoShip]:
        with self.__lock:
            for priority in self.__priorities:
                table = self.__ships.get(priority)
                if table is not None and len(table) > 0:
                    # pop from the head
                    return table.pop(0)


class Docker(Worker):

    def __init__(self, gate: Gate, delegate: GateDelegate):
        super().__init__()
        self.__dock = Dock()
        self.__gate = weakref.ref(gate)
        self.__delegate = weakref.ref(delegate)
        # socket connection
        self.__connection: Optional[Connection] = None
        self.__connection_lock = threading.Lock()
        # waiting ships
        self.__waiting_keys: Set[bytes] = set()
        self.__waiting_ships: Dict[bytes, OutgoShip] = {}
        self.__waiting_lock = threading.Lock()

    @property
    def dock(self) -> Dock:
        return self.__dock

    @property
    def gate(self) -> Gate:
        return self.__gate()

    # Override
    @property
    def delegate(self) -> Optional[GateDelegate]:
        return self.__delegate()

    # Override
    @property
    def status(self) -> ConnectionStatus:
        return self.__connection.get_status(now=time.time())

    def __connect(self, host: str, port: int, sock: Optional[socket.socket] = None) -> Optional[socket.error]:
        if sock is None:
            try:
                sock = socket.socket()
                sock.connect((host, port))
            except socket.error as error:
                traceback.print_exc()
                return error
        # start the connection with socket
        conn = Connection(address=(host, port), sock=sock)
        conn.delegate = self.gate
        conn.start()
        self.__connection = conn

    # Override
    def connect(self, host: str, port: int, sock: Optional[socket.socket] = None) -> Optional[socket.error]:
        with self.__connection_lock:
            # check current connection
            current = self.__connection
            if current is not None:
                if current.port == port and current.host == host:
                    # already connected to the same address(host:port)
                    return None
                # disconnect
                current.stop()
                self.__connection = None
            # connect to new address(host:port)
            return self.__connect(host=host, port=port, sock=sock)

    # Override
    def disconnect(self):
        with self.__connection_lock:
            if self.__connection is not None:
                self.__connection.stop()
                self.__connection = None

    @property
    def current_connection(self) -> Optional[Connection]:
        return self.__connection

    # Override
    def add_task(self, ship: OutgoShip):
        self.__dock.push(ship=ship)

    # Override
    def process(self, count: int) -> int:
        # process incoming packages / outgoing tasks
        if Worker.MAX_INCOMES_PER_OUTGO > 0:
            # incoming priority
            if count < Worker.MAX_INCOMES_PER_OUTGO:
                if self._process_income():
                    return count + 1
            # keep a chance for outgoing packages
            if self._process_outgo():
                return 0
        else:
            # outgoing priority
            assert Worker.MAX_INCOMES_PER_OUTGO != 0, 'cannot set MAX_INCOMES_PER_OUTGO to 0'
            if count > Worker.MAX_INCOMES_PER_OUTGO:
                if self._process_outgo():
                    return count - 1
            # keep a chance for incoming packages
            if self._process_income():
                return 0
        # no task now, send a HEARTBEAT package
        self._process_heartbeat()
        return 0

    @abstractmethod
    def _process_income(self) -> bool:
        raise NotImplemented

    @abstractmethod
    def _process_outgo(self) -> bool:
        raise NotImplemented

    @abstractmethod
    def _process_heartbeat(self) -> bool:
        raise NotImplemented

    def _set_waiting(self, sn: bytes, ship: OutgoShip):
        with self.__waiting_lock:
            self.__waiting_keys.add(sn)
            self.__waiting_ships[sn] = ship

    def _pop_waiting(self, sn: bytes) -> Optional[OutgoShip]:
        with self.__waiting_lock:
            self.__waiting_keys.discard(sn)
            return self.__waiting_ships.pop(sn, None)

    def _get_waiting(self) -> Optional[OutgoShip]:
        """ Get any Ship expired """
        with self.__waiting_lock:
            expired = int(time.time()) - OutgoShip.EXPIRES
            keys = self.__waiting_keys.copy()
            for sn in keys:
                ship = self.__waiting_ships.get(sn)
                if ship is None:
                    self.__waiting_keys.discard(sn)  # should not happen
                    continue
                if ship.time > expired:
                    # not expired yet
                    continue
                if ship.retries < OutgoShip.RETRIES:
                    # got it, update time and retry
                    ship.update()
                    return ship
                # retried too many times
                if ship.time < (expired - OutgoShip.EXPIRES * OutgoShip.RETRIES * 2):
                    # remove timeout task
                    self.__waiting_keys.discard(sn)
                    self.__waiting_ships.pop(sn, None)
