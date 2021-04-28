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

from typing import Optional

from tcp import Connection

from .protocol import WebSocket

from .base import Gate, Ship, StarShip, ShipDelegate
from .dock import Docker


def seq_to_sn(seq: int) -> bytes:
    return seq.to_bytes(length=4, byteorder='big')


class WSShip(StarShip):
    """ Star Ship with WebSocket Package """

    def __init__(self, package: bytes, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None):
        super().__init__(priority=priority, delegate=delegate)
        self.__package = package
        self.__payload = payload

    @property
    def package(self) -> bytes:
        """ Get request will be sent to remote star """
        return self.__package

    # Override
    @property
    def sn(self) -> bytes:
        return self.__payload

    # Override
    @property
    def payload(self) -> bytes:
        return self.__payload


class WSDocker(Docker):
    """ Docker for WebSocket packages """

    def __init__(self, gate: Gate):
        super().__init__(gate=gate)

    @classmethod
    def check(cls, connection: Connection) -> bool:
        # 1. check received data
        buffer = connection.received()
        if buffer is not None:
            return WebSocket.is_handshake(stream=buffer)

    # Override
    def setup(self):
        buffer = self._received_buffer()
        if buffer is not None:
            # remove first handshake package
            self._receive_buffer(length=len(buffer))
            # response for handshake
            res = WebSocket.handshake(stream=buffer)
            self._send_buffer(data=res)

    # Override
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        req_pack = WebSocket.pack(payload=payload)
        req_ship = WSShip(package=req_pack, payload=payload, priority=priority, delegate=delegate)
        return self.dock.put(ship=req_ship)

    def __receive_package(self) -> (Optional[bytes], Optional[bytes]):
        # 1. check received data
        buffer = self._received_buffer()
        if buffer is None:
            # received nothing
            return None, None
        payload, remaining = WebSocket.parse(stream=buffer)
        old_len = len(buffer)
        new_len = len(remaining)
        if new_len < old_len:
            # skip received package
            pack = self._receive_buffer(length=old_len-new_len)
            return pack, payload
        else:
            return None, None

    # Override
    def _get_income_ship(self) -> Optional[Ship]:
        income, payload = self.__receive_package()
        if income is not None:
            return WSShip(package=income, payload=payload)

    # Override
    def _handle_ship(self, income: Ship) -> Optional[StarShip]:
        assert isinstance(income, WSShip), 'income ship error: %s' % income
        body = income.payload
        # 1. check command
        if body is None or len(body) == 0:
            # no more package now
            return None
        elif body == ping_body:
            # respond Command: 'PONG' -> 'PING'
            self.send(payload=pong_body, priority=StarShip.SLOWER)
            return None
        elif income == pong_body:
            # just ignore
            return None
        elif income == noop_body:
            # just ignore
            return None
        # 2. process payload by delegate
        delegate = self.delegate
        if delegate is not None:
            res = delegate.gate_received(gate=self.gate, payload=body)
        else:
            res = None
        # 3. response
        if res is None or len(res) == 0:
            res = ok_body
        req_pack = WebSocket.pack(payload=res)
        return WSShip(package=req_pack, payload=res, priority=StarShip.NORMAL)

    # Override
    def _send_ship(self, outgo: StarShip) -> bool:
        assert isinstance(outgo, WSShip), 'outgo ship error: %s' % outgo
        pack = outgo.package
        # send out request data
        return self._send_buffer(data=pack) == len(pack)

    # Override
    def _get_heartbeat(self) -> Optional[StarShip]:
        req_pack = WebSocket.pack(payload=noop_body)
        return WSShip(package=req_pack, payload=noop_body, priority=StarShip.NORMAL)


#
#  const
#

ping_body = b'PING'
pong_body = b'PONG'
noop_body = b'NOOP'
ok_body = b'OK'
