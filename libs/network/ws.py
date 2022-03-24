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
from typing import Optional, List

from startrek import Arrival, Departure
from startrek import ArrivalShip, DepartureShip, DeparturePriority
from startrek import Connection

from tcp import PlainDocker

from .protocol import WebSocket


class WSArrival(ArrivalShip):

    def __init__(self, package: bytes, payload: bytes):
        super().__init__()
        self.__package = package
        self.__payload = payload

    @property
    def package(self) -> bytes:
        return self.__package

    @property
    def payload(self) -> bytes:
        return self.__payload

    @property  # Override
    def sn(self) -> bytes:
        return self.__payload

    # Override
    def assemble(self, ship):
        assert ship is self, 'arrival ship error: %s, %s' % (ship, self)
        return ship


class WSDeparture(DepartureShip):

    def __init__(self, package: bytes, payload: bytes, priority: int = 0):
        super().__init__(priority=priority, max_tries=DepartureShip.DISPOSABLE)
        self.__fragments = [package]
        self.__package = package
        self.__payload = payload

    @property
    def package(self) -> bytes:
        return self.__package

    @property
    def payload(self) -> bytes:
        return self.__payload

    @property  # Override
    def sn(self) -> bytes:
        return self.__payload

    @property  # Override
    def fragments(self) -> List[bytes]:
        return self.__fragments

    # Override
    def check_response(self, ship: Arrival) -> bool:
        # assert isinstance(ship, WSArrival), 'arrival ship error: %s' % ship
        assert ship.sn == self.sn, 'SN not match: %s, %s' % (ship.sn, self.sn)
        self.__fragments.clear()
        return True


class WSDocker(PlainDocker):
    """ Docker for WebSocket packages """

    MAX_PACK_LENGTH = 65536  # 64 KB

    def __init__(self, connection: Connection):
        super().__init__(connection=connection)
        self.__handshaking = True
        self.__chunks = b''
        self.__chunks_lock = threading.RLock()
        self.__package_received = False

    def _parse_package(self, data: bytes) -> (Optional[bytes], Optional[bytes]):
        with self.__chunks_lock:
            # join the data to the memory cache
            data = self.__chunks + data
            self.__chunks = b''
            # try to fetch a package
            payload, remaining = WebSocket.parse(stream=data)
            tail_len = len(remaining)
            if tail_len > 0:
                # put the remaining data back to memory cache
                self.__chunks = remaining + self.__chunks
            pack = None
            if payload is not None:
                data_len = len(data)
                pack_len = data_len - tail_len
                if pack_len > 0:
                    pack = data[:pack_len]
            return pack, payload

    # Override
    def process_received(self, data: bytes):
        # the cached data maybe contain sticky packages,
        # so we need to process them circularly here
        self.__package_received = True
        while self.__package_received:
            self.__package_received = False
            super().process_received(data=data)
            data = b''

    # Override
    def _get_arrival(self, data: bytes) -> Optional[Arrival]:
        # check for first request
        if self.__handshaking:
            # join the data to the memory cache
            data = self.__chunks + data
            self.__chunks = b''
            # parse handshake
            res = WebSocket.handshake(stream=data)
            if res is not None:
                ship = WSDeparture(package=res, payload=b'')
                self.send_ship(ship=ship)
                self.__handshaking = False
            elif len(data) < self.MAX_PACK_LENGTH:
                # waiting for more data
                self.__chunks = data + self.__chunks
        else:
            # normal state
            pack, payload = self._parse_package(data=data)
            if pack is not None:
                return WSArrival(package=pack, payload=payload)

    # Override
    def _check_arrival(self, ship: Arrival) -> Optional[Arrival]:
        assert isinstance(ship, WSArrival), 'arrival ship error: %s' % ship
        body = ship.payload
        body_len = len(body)
        # 1. check command
        if body_len == 0:
            # data empty
            return None
        elif body_len == 4:
            if body == PING:
                # 'PING' -> 'PONG'
                ship = self.pack(payload=PONG, priority=DeparturePriority.SLOWER)
                self.send_ship(ship=ship)
                return None
            elif body == PONG or body == NOOP:
                # ignore
                return None
        elif body == OK:
            # should not happen
            return None
        # NOTICE: the delegate must respond to client in current request,
        #         cause it's a HTTP connection
        return ship

    # Override
    def heartbeat(self):
        # heartbeat by client
        pass

    # noinspection PyMethodMayBeStatic
    def pack(self, payload: bytes, priority: int = 0) -> Departure:
        req_pack = WebSocket.pack(payload=payload)
        return WSDeparture(package=req_pack, payload=payload, priority=priority)

    @classmethod
    def check(cls, data: bytes) -> bool:
        return WebSocket.is_handshake(stream=data)


#
#  const
#

PING = b'PING'
PONG = b'PONG'
NOOP = b'NOOP'
OK = b'OK'
