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

from .protocol import NetMsg, NetMsgHead

from .ship import Ship, ShipDelegate
from .starship import StarShip
from .docker import Docker
from .gate import Gate


def seq_to_sn(seq: int) -> bytes:
    return seq.to_bytes(length=4, byteorder='big')


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
        return seq_to_sn(seq=self.__mars.head.seq)

    # Override
    @property
    def payload(self) -> bytes:
        return self.__mars.body


class MarsDocker(Docker):
    """ Docker for Mars packages """

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
            return head

    @classmethod
    def check(cls, connection: Connection) -> bool:
        # 1. check received data
        buffer = connection.received()
        if buffer is not None:
            return cls.parse_head(buffer=buffer) is not None

    # Override
    def pack(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> StarShip:
        head = NetMsgHead.new(cmd=NetMsgHead.PUSH_MESSAGE, body_len=len(payload))
        mars = NetMsg.new(head=head, body=payload)
        return MarsShip(mars=mars, priority=priority, delegate=delegate)

    def __receive_package(self) -> Optional[NetMsg]:
        # 1. check received data
        data = self.gate.received()
        if data is None:
            # received nothing
            return None
        data_len = len(data)
        head = self.parse_head(buffer=data)
        if head is None:
            # not a MTP package?
            if data_len < NetMsgHead.MIN_HEAD_LEN:
                # wait for more data
                return None
            pos = data.find(NetMsgHead.MAGIC_CODE, NetMsgHead.MAGIC_CODE_OFFSET+1)
            if pos > NetMsgHead.MAGIC_CODE_OFFSET:
                # found next head, skip data before it
                self.gate.receive(length=pos-NetMsgHead.MAGIC_CODE_OFFSET)
            else:
                # skip the whole data
                self.gate.receive(length=data_len)
            # take it as NOOP
            head = NetMsgHead.new(cmd=NetMsgHead.NOOP)
            return NetMsg.new(head=head)
        # 2. receive data with 'head.length + body.length'
        body_len = head.body_length
        if body_len < 0:
            # should not happen
            body_len = data_len - head.length
        pack_len = head.length + body_len
        if pack_len > data_len:
            # waiting for more data
            return None
        # receive package
        data = self.gate.receive(length=pack_len)
        if body_len > 0:
            body = data[head.length:]
        else:
            body = None
        return NetMsg(data=data, head=head, body=body)

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
        # elif cmd == NetMsgHead.PUSH_MESSAGE:
        #     # remove linked outgo Ship
        #     super()._process_income_ship(income=income)
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
            head = NetMsgHead.new(cmd=cmd, seq=head.seq, body_len=len(res))
            mars = NetMsg.new(head=head, body=res)
            # send it directly
            self.gate.send(data=mars.data)
        else:
            return self.pack(payload=res, priority=StarShip.SLOWER)

    # # Override
    # def _send_outgo_ship(self, outgo: StarShip) -> bool:
    #     assert isinstance(outgo, MarsShip), 'outgo ship error: %s' % outgo
    #     mars = outgo.mars
    #     # check data type
    #     if mars.head.cmd == NetMsgHead.PUSH_MESSAGE:
    #         # put back for response
    #         self.gate.put(ship=outgo)
    #     # send out request data
    #     return super()._send_outgo_ship(outgo=outgo)

    # Override
    def _get_heartbeat(self) -> Optional[StarShip]:
        pass


#
#  const
#

ping_body = b'PING'
pong_body = b'PONG'
noop_body = b'NOOP'
