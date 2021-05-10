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

from startrek import Gate
from startrek import Ship, ShipDelegate
from startrek import StarShip
from startrek import StarDocker

from .protocol import NetMsg, NetMsgHead, NetMsgSeq


def seq_to_sn(seq: int) -> bytes:
    return seq.to_bytes(length=4, byteorder='big')


def fetch_sn(body: bytes) -> Optional[bytes]:
    if body is not None and body.startswith(b'Mars SN:'):
        pos = body.find(b'\n')
        assert pos > 8, 'Mars SN error: %s' % body
        return body[8:pos]


class MarsShip(StarShip):
    """ Star Ship with Mars Package """

    def __init__(self, mars: NetMsg, priority: int = 0, delegate: Optional[ShipDelegate] = None):
        super().__init__(priority=priority, delegate=delegate)
        self.__mars = mars

    @property
    def mars(self) -> NetMsg:
        """ Get request will be sent to remote star """
        return self.__mars

    @property
    def package(self) -> bytes:
        return self.__mars.data

    # Override
    @property
    def sn(self) -> bytes:
        sn = fetch_sn(body=self.__mars.body)
        if sn is None:
            return seq_to_sn(seq=self.__mars.head.seq)
        else:
            return sn

    # Override
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


class MarsDocker(StarDocker):
    """ Docker for Mars packages """

    MAX_HEAD_LENGTH = NetMsgHead.MIN_HEAD_LEN + 12  # FIXME: len(options) > 12?

    def __init__(self, gate: Gate):
        super().__init__(gate=gate)

    @classmethod
    def parse_head(cls, buffer: bytes) -> Optional[NetMsgHead]:
        head = NetMsgHead.parse(data=buffer)
        if head is not None:
            if head.version != 200:
                return None
            if head.cmd not in [NetMsgHead.SEND_MSG, NetMsgHead.NOOP, NetMsgHead.PUSH_MESSAGE]:
                return None
            if head.body_length < 0:
                return None
            return head

    @classmethod
    def check(cls, gate: Gate) -> bool:
        buffer = gate.receive(length=cls.MAX_HEAD_LENGTH, remove=False)
        if buffer is not None:
            return cls.parse_head(buffer=buffer) is not None

    # Override
    def pack(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> StarShip:
        seq = NetMsgSeq.generate()
        sn = seq.to_bytes(length=4, byteorder='big')
        body = b'Mars SN:' + sn + b'\n' + payload
        # pack sn + payload
        head = NetMsgHead.new(cmd=NetMsgHead.PUSH_MESSAGE, body_len=len(body))
        mars = NetMsg.new(head=head, body=body)
        return MarsShip(mars=mars, priority=priority, delegate=delegate)

    def __seek_header(self) -> Optional[NetMsgHead]:
        buffer = self.gate.receive(length=512, remove=False)
        if buffer is None:
            # received nothing
            return None
        head = self.parse_head(buffer=buffer)
        if head is None:
            buf_len = len(buffer)
            # not a Mars package?
            if buf_len < self.MAX_HEAD_LENGTH:
                # wait for more data
                return None
            # locate next header
            pos = buffer.find(NetMsgHead.MAGIC_CODE, NetMsgHead.MAGIC_CODE_OFFSET+1)
            if pos > NetMsgHead.MAGIC_CODE_OFFSET:
                # found next head, skip data before it
                self.gate.receive(length=pos-NetMsgHead.MAGIC_CODE_OFFSET, remove=True)
            elif buf_len > 500:
                # skip the whole buffer
                self.gate.receive(length=buf_len, remove=True)
        return head

    def __receive_package(self) -> Optional[NetMsg]:
        # 1. seek header in received data
        head = self.__seek_header()
        if head is None:
            # # take it as NOOP
            # head = NetMsgHead.new(cmd=NetMsgHead.NOOP)
            # return NetMsg.new(head=head)
            return None
        body_len = head.body_length
        assert body_len >= 0, 'body length error: %d' % body_len
        pack_len = head.length + body_len
        # 2. receive data with 'head.length + body.length'
        buffer = self.gate.receive(length=pack_len, remove=False)
        if len(buffer) < pack_len:
            # waiting for more data
            return None
        # receive package (remove from gate)
        buffer = self.gate.receive(length=pack_len, remove=True)
        if body_len > 0:
            body = buffer[head.length:]
        else:
            body = None
        return NetMsg(data=buffer, head=head, body=body)

    # Override
    def _get_income_ship(self) -> Optional[Ship]:
        income = self.__receive_package()
        if income is not None:
            return MarsShip(mars=income)

    # Override
    def _process_income_ship(self, income: Ship) -> Optional[StarShip]:
        assert isinstance(income, MarsShip), 'income ship error: %s' % income
        mars = income.mars
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
            if len(body) == 0 or body == noop_body:
                return income
        # 2. process payload by delegate
        res = None
        if body == ping_body:
            res = pong_body
        elif body == pong_body:
            # FIXME: client should not send 'PONG' to server
            return None
        elif body == noop_body:
            # FIXME: 'NOOP' can only sent by NOOP cmd
            return None
        else:
            delegate = self.gate.delegate
            if delegate is not None:
                res = delegate.gate_received(gate=self.gate, ship=income)
        if res is None:
            res = b''
        # 3. response
        if cmd in [NetMsgHead.NOOP, NetMsgHead.SEND_MSG]:
            # pack with request.seq
            head = NetMsgHead.new(cmd=cmd, seq=head.seq, body_len=len(res))
            mars = NetMsg.new(head=head, body=res)
            return MarsShip(mars=mars)
        else:
            # pack and put into waiting queue
            return self.pack(payload=res, priority=StarShip.SLOWER)

    # Override
    def _remove_linked_ship(self, income: Ship):
        assert isinstance(income, MarsShip), 'income ship error: %s' % income
        if income.mars.head.cmd == NetMsgHead.SEND_MSG:
            super()._remove_linked_ship(income=income)

    # Override
    def _get_outgo_ship(self, income: Optional[Ship] = None) -> Optional[StarShip]:
        outgo = super()._get_outgo_ship(income=income)
        if income is None and isinstance(outgo, MarsShip):
            # if retries == 0, means this ship is first time to be sent,
            # and it would be removed from the dock.
            if outgo.retries == 0 and outgo.mars.head.cmd == NetMsgHead.PUSH_MESSAGE:
                # put back for waiting response
                self.gate.park_ship(ship=outgo)
        return outgo

    # Override
    def _get_heartbeat(self) -> Optional[StarShip]:
        pass


#
#  const
#

ping_body = b'PING'
pong_body = b'PONG'
noop_body = b'NOOP'
