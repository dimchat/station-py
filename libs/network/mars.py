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
import weakref
from typing import Optional, List

from dimp import utf8_encode, utf8_decode, base64_encode, base64_decode

from startrek import ShipDelegate, Arrival, Departure, DeparturePriority
from startrek import ArrivalShip, DepartureShip
from startrek import Hub, StarGate

from udp.ba import Data
from tcp import PlainDocker

from .protocol import NetMsg, NetMsgHead, NetMsgSeq
from .seeker import MarsPackageSeeker


def encode_sn(sn: bytes) -> bytes:
    """ Encode to Base-64 """
    return utf8_encode(string=base64_encode(data=sn))


def decode_sn(sn: bytes) -> bytes:
    """ Decode from Base-64 """
    return base64_decode(string=utf8_decode(data=sn))


def seq_to_sn(seq: int) -> bytes:
    return seq.to_bytes(length=4, byteorder='big')


def fetch_sn(body: bytes) -> Optional[bytes]:
    if body is not None and body.startswith(b'Mars SN:'):
        pos = body.find(b'\n', 8)
        assert pos > 8, 'Mars SN error: %s' % body
        return body[8:pos]


def get_sn(mars: NetMsg) -> bytes:
    sn = fetch_sn(body=mars.body)
    if sn is None:
        sn = seq_to_sn(seq=mars.head.seq)
    else:
        sn = decode_sn(sn=sn)
    return sn


def parse_head(data: bytes) -> Optional[NetMsgHead]:
    head = NetMsgHead.parse(data=data)
    if head is not None:
        if head.version != 200:
            return None
        if head.cmd not in [NetMsgHead.SEND_MSG, NetMsgHead.NOOP, NetMsgHead.PUSH_MESSAGE]:
            return None
        if head.body_length < 0:
            return None
        return head


class MarsHelper:

    seeker = MarsPackageSeeker()

    @classmethod
    def seek_header(cls, data: bytes) -> (Optional[NetMsgHead], int):
        data = Data(buffer=data)
        return cls.seeker.seek_header(data=data)

    @classmethod
    def seek_package(cls, data: bytes) -> (Optional[NetMsg], int):
        data = Data(buffer=data)
        return cls.seeker.seek_package(data=data)

    @classmethod
    def create_respond(cls, head: NetMsgHead, payload: bytes) -> NetMsg:
        """ create for SEND_MSG, NOOP """
        cmd = head.cmd
        seq = head.seq
        assert cmd in [NetMsgHead.SEND_MSG, NetMsgHead.NOOP], 'cmd error: %s' % cmd
        body = payload
        head = NetMsgHead.new(cmd=cmd, seq=seq, body_len=len(body))
        return NetMsg.new(head=head, body=body)

    @classmethod
    def create_push(cls, payload: bytes) -> NetMsg:
        """ create for PUSH_MESSAGE """
        seq = NetMsgSeq.generate()
        sn = seq_to_sn(seq=seq)
        sn = encode_sn(sn=sn)
        # pack 'sn + payload'
        body = b'Mars SN:' + sn + b'\n' + payload
        head = NetMsgHead.new(cmd=NetMsgHead.PUSH_MESSAGE, body_len=len(body))
        return NetMsg.new(head=head, body=body)


class MarsStreamArrival(ArrivalShip):
    """ Mars Stream Arrival Ship """

    def __init__(self, mars: NetMsg):
        super().__init__()
        self.__mars = mars
        self.__sn = get_sn(mars=self.__mars)

    @property
    def package(self) -> NetMsg:
        return self.__mars

    @property
    def payload(self) -> Optional[bytes]:
        body = self.__mars.body
        sn = fetch_sn(body=body)
        if sn is None:
            return body
        else:
            # pos = body.find(b'\n')
            # return body[pos+1:]
            skip = 8 + len(sn) + 1
            return body[skip:]

    @property  # Override
    def sn(self) -> bytes:
        return self.__sn

    # Override
    def assemble(self, ship):
        assert self is ship, 'mars arrival error: %s, %s' % (ship, self)
        return ship


class MarsStreamDeparture(DepartureShip):
    """ Mars Stream Departure Ship """

    def __init__(self, mars: NetMsg, priority: int = 0, delegate: Optional[ShipDelegate] = None):
        super().__init__(priority=priority, delegate=delegate)
        self.__mars = mars
        self.__sn = get_sn(mars=mars)
        self.__fragments = [mars.data]

    @property
    def package(self) -> NetMsg:
        return self.__mars

    @property  # Override
    def sn(self) -> bytes:
        return self.__sn

    @property  # Override
    def fragments(self) -> List[bytes]:
        return self.__fragments

    # Override
    def check_response(self, ship: Arrival) -> bool:
        assert isinstance(ship, MarsStreamArrival), 'arrival ship error: %s' % ship
        assert ship.sn == self.sn, 'SN not match: %s, %s' % (ship.sn, self.sn)
        self.__fragments.clear()
        return True


class MarsStreamDocker(PlainDocker):
    """ Docker for Mars packages """

    def __init__(self, remote: tuple, local: Optional[tuple], gate: StarGate, hub: Hub):
        super().__init__(remote=remote, local=local, gate=gate)
        self.__hub = weakref.ref(hub)
        self.__chunks = b''
        self.__chunks_lock = threading.RLock()
        self.__package_received = False

    @property
    def hub(self) -> Hub:
        return self.__hub()

    def _parse_package(self, data: bytes) -> Optional[NetMsg]:
        with self.__chunks_lock:
            # join the data to the memory cache
            data = self.__chunks + data
            self.__chunks = b''
            # try to fetch a package
            pack, offset = MarsHelper.seek_package(data=data)
            self.__package_received = pack is not None
            if offset >= 0:
                # 'error part' + 'mars package' + 'remaining data
                if pack is not None:
                    offset += pack.length
                if offset == 0:
                    self.__chunks = data + self.__chunks
                elif offset < len(data):
                    data = data[offset:]
                    self.__chunks = data + self.__chunks
            return pack

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
        pack = self._parse_package(data=data)
        if pack is None:
            return None
        # if pack.body is None:
        #     return None
        return MarsStreamArrival(mars=pack)

    # Override
    def _check_arrival(self, ship: Arrival) -> Optional[Arrival]:
        assert isinstance(ship, MarsStreamArrival), 'arrival ship error: %s' % ship
        payload = ship.payload
        if payload is None:
            body_len = 0
        else:
            body_len = len(payload)
        mars = ship.package
        head = mars.head
        # 1. check head cmd
        cmd = head.cmd
        if cmd == NetMsgHead.SEND_MSG:
            # handle SEND_MSG request
            if mars.body is None:
                # FIXME: should not happen
                return None
        elif cmd == NetMsgHead.NOOP:
            # handle NOOP request
            if body_len == 0 or payload == NOOP:
                ship = self.create_departure(mars=mars, priority=DeparturePriority.SLOWER)
                self.append_departure(ship=ship)
                return None
        # 2. check body
        if body_len == 4:
            if payload == PING:
                mars = MarsHelper.create_respond(head=head, payload=PONG)
                ship = self.create_departure(mars=mars, priority=DeparturePriority.SLOWER)
                self.append_departure(ship=ship)
                return None
            elif payload == PONG:
                # FIXME: client should not sent 'PONG' to server
                return None
            elif payload == NOOP:
                # FIXME: 'NOOP' can only sent by NOOP cmd
                return None
        # 3. check for response
        self._check_response(ship=ship)
        # NOTICE: the delegate must respond mars package with same cmd & seq,
        #         otherwise the connection will be closed by client
        return ship

    # Override
    def _next_departure(self, now: int) -> Optional[Departure]:
        outgo = super()._next_departure(now=now)
        if outgo is not None:
            self._retry_departure(ship=outgo)
        return outgo

    def _retry_departure(self, ship: Departure):
        if ship.retries >= DepartureShip.MAX_RETRIES:
            # last try
            return False
        if isinstance(ship, MarsStreamDeparture):
            pack = ship.package
            cmd = pack.head.cmd
            if cmd == NetMsgHead.PUSH_MESSAGE:
                # put back for next retry
                self.append_departure(ship=ship)
                return True

    # Override
    def pack(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> Departure:
        mars = MarsHelper.create_push(payload=payload)
        return self.create_departure(mars=mars, priority=priority, delegate=delegate)

    # Override
    def heartbeat(self):
        # heartbeat by client
        pass

    @classmethod
    def create_departure(cls, mars: NetMsg, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> Departure:
        return MarsStreamDeparture(mars=mars, priority=priority, delegate=delegate)

    @classmethod
    def check(cls, data: bytes) -> bool:
        head, offset = MarsHelper.seek_header(data=data)
        return head is not None


#
#  const
#

PING = b'PING'
PONG = b'PONG'
NOOP = b'NOOP'
OK = b'OK'
