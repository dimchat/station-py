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

from typing import Optional, List

from startrek import ShipDelegate, Arrival, Departure, DeparturePriority
from startrek import ArrivalShip, DepartureShip
from startrek import StarGate

from tcp import PlainDocker

from .protocol import NetMsg, NetMsgHead, NetMsgSeq


def seq_to_sn(seq: int) -> bytes:
    return seq.to_bytes(length=4, byteorder='big')


def fetch_sn(body: bytes) -> Optional[bytes]:
    if body is not None and body.startswith(b'Mars SN:'):
        pos = body.find(b'\n')
        assert pos > 8, 'Mars SN error: %s' % body
        return body[8:pos]


def get_sn(mars: NetMsg) -> bytes:
    sn = fetch_sn(body=mars.body)
    if sn is None:
        sn = seq_to_sn(seq=mars.head.seq)
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

    MAGIC_CODE = NetMsgHead.MAGIC_CODE
    MAGIC_CODE_OFFSET = NetMsgHead.MAGIC_CODE_OFFSET

    MAX_HEAD_LENGTH = NetMsgHead.MIN_HEAD_LEN + 12  # FIXME: len(options) > 12?

    @classmethod
    def seek_header(cls, data: bytes) -> (Optional[NetMsgHead], int):
        head = parse_head(data=data)
        if head is not None:
            # got it (offset = 0)
            return head, 0
        data_len = len(data)
        if data_len < cls.MAX_HEAD_LENGTH:
            # waiting for more data
            return None, 0
        # locate next header
        offset = data.find(cls.MAGIC_CODE, cls.MAGIC_CODE_OFFSET + 1)
        if offset == -1:
            if data_len < 65536:
                # waiting for more data
                return None, 0
            # skip the whole buffer
            return None, -1
        assert offset > cls.MAGIC_CODE_OFFSET, 'magic code error: %s' % data
        # found next header, skip data before it
        offset -= cls.MAGIC_CODE_OFFSET
        data = data[offset:]
        # try again from new offset
        return parse_head(data=data), offset

    @classmethod
    def parse(cls, data: bytes) -> (Optional[NetMsg], int):
        # 1. seek header in received data
        head, offset = cls.seek_header(data=data)
        if offset < 0:
            # data error, ignore the whole buffer
            return None, -1
        if head is None:
            # header not found
            return None, offset
        if offset > 0:
            # drop the error part
            data = data[offset:]
        # 2. check length
        data_len = len(data)
        head_len = head.length
        body_len = head.body_length
        if body_len < 0:
            pack_len = data_len
        else:
            pack_len = head_len + body_len
        if data_len < pack_len:
            # package not completed, waiting for more data
            return None, offset
        elif data_len > pack_len:
            # cut the tail
            data = data[:pack_len]
        if head_len < pack_len:
            body = data[head_len:]
        else:
            body = None
        return NetMsg(data=data, head=head, body=body), offset

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
        cmd = NetMsgHead.PUSH_MESSAGE
        seq = NetMsgSeq.generate()
        # pack 'sn + payload'
        sn = seq.to_bytes(length=4, byteorder='big')
        body = b'Mars SN:' + sn + b'\n' + payload
        head = NetMsgHead.new(cmd=cmd, body_len=len(body))
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
    def payload(self) -> bytes:
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
        self.__sn = get_sn(mars=self.__mars)
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

    def __init__(self, remote: tuple, local: Optional[tuple], gate: StarGate):
        super().__init__(remote=remote, local=local, gate=gate)
        self.__chunks = b''
        self.__processing = 0

    def __append_cache(self, data: bytes):
        """ Append the data to the tail of memory cache """
        self.__chunks = self.__chunks + data

    def __join_cache(self, data: bytes) -> bytes:
        """ Join the memory cache and new data """
        chunks = self.__chunks + data
        self.__chunks = b''
        return chunks

    def __push_back(self, data: bytes):
        """ Put the remaining data back to memory cache """
        self.__chunks = data + self.__chunks

    def __parse_package(self, data: bytes) -> Optional[NetMsg]:
        self.__processing += 1
        if self.__processing > 1:
            # it's already in processing now,
            # append the data to the tail of memory cache
            self.__append_cache(data=data)
            self.__processing -= 1
            return None
        # join the data to the memory cache
        data = self.__join_cache(data=data)
        # try to fetch a package
        pack, offset = MarsHelper.parse(data=data)
        if offset < 0:
            # data error
            self.__processing -= 1
            return None
        # 'error part' + 'mars package' + 'remaining data
        if pack is not None:
            offset += pack.length
        if offset == 0:
            self.__push_back(data=data)
        elif offset < len(data):
            data = data[offset:]
            self.__push_back(data=data)
        self.__processing -= 1
        return pack

    # Override
    def process_received(self, data: bytes):
        # the cached data maybe contain sticky packages,
        # so we need to process them circularly here
        old_len = 0
        new_len = len(data)
        while new_len > 0 and new_len != old_len:
            old_len = len(self.__chunks)
            super().process_received(data=data)
            new_len = len(self.__chunks)
            data = b''

    # Override
    def get_arrival(self, data: bytes) -> Optional[Arrival]:
        pack = self.__parse_package(data=data)
        if pack is None:
            return None
        # if pack.body is None:
        #     return None
        return MarsStreamArrival(mars=pack)

    # Override
    def check_arrival(self, ship: Arrival) -> Optional[Arrival]:
        assert isinstance(ship, MarsStreamArrival), 'arrival ship error: %s' % ship
        mars = ship.package
        head = mars.head
        body = mars.body
        if body is None:
            body = b''
        # 1. check head cmd
        cmd = head.cmd
        if cmd == NetMsgHead.SEND_MSG:
            # handle SEND_MSG request
            if len(body) == 0:
                # FIXME: should not happen
                return None
        elif cmd == NetMsgHead.NOOP:
            # handle NOOP request
            if len(body) == 0 or body == NOOP:
                ship = self.create_departure(mars=mars, priority=DeparturePriority.SLOWER)
                self.append_departure(ship=ship)
                return None
        # 2. check body
        if len(body) == 4:
            if body == PING:
                mars = MarsHelper.create_respond(head=head, payload=PONG)
                ship = self.create_departure(mars=mars, priority=DeparturePriority.SLOWER)
                self.append_departure(ship=ship)
                return None
            elif body == PONG:
                # FIXME: client should not sent 'PONG' to server
                return None
            elif body == NOOP:
                # FIXME: 'NOOP' can only sent by NOOP cmd
                return None
        # 3. check for response
        self.check_response(ship=ship)
        # NOTICE: the delegate mast respond mars package with same cmd & seq,
        #         otherwise the connection will be closed by client
        return ship

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
