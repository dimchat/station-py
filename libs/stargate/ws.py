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

import time
import weakref
from typing import Optional

from tcp import Connection

from .protocol import WebSocket

from .base import Gate, GateDelegate
from .base import OutgoShip
from .dock import Docker


def seq_to_sn(seq: int) -> bytes:
    return seq.to_bytes(length=4, byteorder='big')


class WSShip(OutgoShip):
    """ Star Ship with WebSocket Package """

    def __init__(self, package: bytes, payload: bytes, priority: int = 0, delegate: Optional[GateDelegate] = None):
        super().__init__()
        self.__package = package
        self.__payload = payload
        self.__priority = priority
        # retry
        self.__timestamp = 0
        self.__retries = 0
        # callback
        if delegate is None:
            self.__delegate = None
        else:
            self.__delegate = weakref.ref(delegate)

    # Override
    @property
    def delegate(self) -> Optional[GateDelegate]:
        """ Get request handler """
        if self.__delegate is not None:
            return self.__delegate()

    # Override
    @property
    def priority(self) -> int:
        return self.__priority

    # Override
    @property
    def time(self) -> int:
        return self.__timestamp

    # Override
    @property
    def retries(self) -> int:
        return self.__retries

    # Override
    def update(self):
        self.__timestamp = int(time.time())
        self.__retries += 1
        return self

    @property
    def package(self) -> bytes:
        """ Get request will be sent to remote star """
        return self.__package

    # Override
    @property
    def sn(self) -> bytes:
        return self.payload

    # Override
    @property
    def payload(self) -> bytes:
        return self.__payload


class WSDocker(Docker):
    """ Docker for WebSocket packages """

    def __init__(self, gate: Gate):
        super().__init__(gate=gate)
        # time for checking heartbeat
        self.__heartbeat_expired = int(time.time())

    @classmethod
    def check(cls, connection: Connection) -> bool:
        # 1. check received data
        buffer = connection.received()
        if buffer is not None:
            return WebSocket.is_handshake(stream=buffer)

    # Override
    def setup(self):
        buffer = self.connection.received()
        if buffer is not None:
            # remove first handshake package
            self.connection.receive(length=len(buffer))
            # response for handshake
            res = WebSocket.handshake(stream=buffer)
            self.__send_package(pack=res)

    # Override
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[GateDelegate] = None) -> bool:
        req_pack = WebSocket.pack(payload=payload)
        req_ship = WSShip(package=req_pack, payload=payload, priority=priority, delegate=delegate)
        return self.dock.put(ship=req_ship)

    def __send_package(self, pack: bytes) -> int:
        conn = self.connection
        if conn is None:
            # connection lost
            return -1
        return conn.send(data=pack)

    def __receive_payload(self) -> Optional[bytes]:
        conn = self.connection
        if conn is None:
            # connection lost
            return None
        # 1. check received data
        buffer = conn.received()
        if buffer is None:
            # received nothing
            return None
        data, remaining = WebSocket.parse(stream=buffer)
        old_len = len(buffer)
        new_len = len(remaining)
        if new_len < old_len:
            # skip received package
            conn.receive(length=old_len-new_len)
        # return received payload
        return data

    # Override
    def _handle_income(self) -> bool:
        income = self.__receive_payload()
        if income is None:
            # no more package now
            return False
        elif income == ping_body:
            # respond Command: 'PONG' -> 'PING'
            self.send(payload=pong_body, priority=OutgoShip.SLOWER)
            return True
        elif income == pong_body:
            # just ignore
            return True
        elif income == noop_body:
            # just ignore
            return True
        elif len(income) > 0:
            # process received payload
            delegate = self.delegate
            if delegate is not None:
                res = delegate.gate_received(gate=self.gate, payload=income)
                if res is not None and len(res) > 0:
                    self.send(payload=res, priority=OutgoShip.NORMAL, delegate=delegate)
        # float control
        if Gate.INCOME_INTERVAL > 0:
            time.sleep(Gate.INCOME_INTERVAL)
        return True

    # Override
    def _handle_outgo(self) -> bool:
        # get next new task (time == 0)
        ship = self.dock.pop()
        if ship is None:
            # no more new task now, get any expired task
            ship = self.dock.any()
            if ship is None:
                # no task expired now
                return False
            elif ship.expired:
                # remove an expired task
                delegate = ship.delegate
                if delegate is not None:
                    error = TimeoutError('Request timeout')
                    delegate.gate_sent(gate=self.gate, payload=ship.payload, error=error)
                return True
        assert isinstance(ship, WSShip), 'outgo ship error: %s' % ship
        outgo = ship.package
        # send out request data
        res = self.__send_package(pack=outgo)
        if res != len(outgo):
            # callback for sent failed
            delegate = ship.delegate
            if delegate is not None:
                error = ConnectionError('Socket error')
                delegate.gate_sent(gate=self.gate, payload=ship.payload, error=error)
        # flow control
        if Gate.OUTGO_INTERVAL > 0:
            time.sleep(Gate.OUTGO_INTERVAL)
        return True

    # Override
    def _handle_heartbeat(self):
        # check time for next heartbeat
        now = time.time()
        if now > self.__heartbeat_expired:
            conn = self.connection
            if conn.is_expired(now=now):
                self.send(payload=ping_body, priority=OutgoShip.SLOWER)
            # try heartbeat next 2 seconds
            self.__heartbeat_expired = now + 2
        # idling
        assert Gate.IDLE_INTERVAL > 0, 'IDLE_INTERVAL error'
        time.sleep(Gate.IDLE_INTERVAL)


#
#  const
#

ping_body = b'PING'
pong_body = b'PONG'
noop_body = b'NOOP'
