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

from udp.ba import Data
from udp.mtp import Package, Header, DataType


class MTPShip(StarShip):
    """ Star Ship with MTP Package """

    def __init__(self, mtp: Package, priority: int = 0, delegate: Optional[ShipDelegate] = None):
        super().__init__(priority=priority, delegate=delegate)
        self.__mtp = mtp

    @property
    def mtp(self) -> Package:
        """ Get request will be sent to remote star """
        return self.__mtp

    @property
    def package(self) -> bytes:
        return self.__mtp.get_bytes()

    # Override
    @property
    def sn(self) -> bytes:
        return self.__mtp.head.sn.get_bytes()

    # Override
    @property
    def payload(self) -> bytes:
        return self.__mtp.body.get_bytes()


class MTPDocker(StarDocker):
    """ Docker for MTP packages """

    MAX_HEAD_LENGTH = 24

    def __init__(self, gate: Gate):
        super().__init__(gate=gate)

    @classmethod
    def parse_head(cls, buffer: bytes) -> Optional[Header]:
        data = Data(buffer=buffer)
        head = Header.parse(data=data)
        if head is not None:
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
        req = Data(buffer=payload)
        mtp = Package.new(data_type=DataType.MESSAGE, body_length=req.size, body=req)
        return MTPShip(mtp=mtp, priority=priority, delegate=delegate)

    def __seek_header(self) -> Optional[Header]:
        buffer = self.gate.receive(length=512, remove=False)
        if buffer is None:
            # received nothing
            return None
        head = self.parse_head(buffer=buffer)
        if head is None:
            buf_len = len(buffer)
            # not a MTP package?
            if buf_len < self.MAX_HEAD_LENGTH:
                # wait for more data
                return None
            # locate next header
            pos = buffer.find(Header.MAGIC_CODE, 1)  # MAGIC_CODE_OFFSET = 0
            if pos > 0:
                # found next head(starts with 'DIM'), skip data before it
                self.gate.receive(length=pos, remove=True)
            elif buf_len > 500:
                # skip the whole buffer
                self.gate.receive(length=buf_len, remove=True)
        return head

    def __receive_package(self) -> Optional[Package]:
        # 1. seek header in received data
        head = self.__seek_header()
        if head is None:
            # header not found
            return None
        body_len = head.body_length
        assert body_len >= 0, 'body length error: %d' % body_len
        pack_len = head.size + body_len
        # 2. receive data with 'head.length + body.length'
        buffer = self.gate.receive(length=pack_len, remove=False)
        if buffer is None or len(buffer) < pack_len:
            # waiting for more data
            return None
        else:
            # remove from gate
            self.gate.receive(length=pack_len, remove=True)
        data = Data(buffer=buffer)
        body = data.slice(start=head.size)
        return Package(data=data, head=head, body=body)

    # Override
    def get_income_ship(self) -> Optional[Ship]:
        income = self.__receive_package()
        if income is not None:
            return MTPShip(mtp=income)

    # Override
    def process_income_ship(self, income: Ship) -> Optional[StarShip]:
        assert isinstance(income, MTPShip), 'income ship error: %s' % income
        mtp = income.mtp
        head = mtp.head
        body = mtp.body
        # 1. check data type
        data_type = head.data_type
        if data_type == DataType.COMMAND:
            # respond for Command directly
            if body == ping_body:  # 'PING'
                res = pong_body    # 'PONG'
                mtp = Package.new(data_type=DataType.COMMAND_RESPONSE, sn=head.sn, body_length=res.size, body=res)
                return MTPShip(mtp=mtp, priority=StarShip.SLOWER)
            return None
        elif data_type == DataType.COMMAND_RESPONSE:
            # just ignore
            return None
        elif data_type == DataType.MESSAGE_FRAGMENT:
            # just ignore
            return None
        elif data_type == DataType.MESSAGE_RESPONSE:
            if body.size == 0 or body == ok_body:
                # just ignore
                return None
            elif body == again_body:
                # TODO: mission failed, send the message again
                return None
        # 2. process payload by delegate
        delegate = self.gate.delegate
        if body.size > 0 and delegate is not None:
            res = delegate.gate_received(gate=self.gate, ship=income)
        else:
            res = None
        # 3. response
        if data_type == DataType.MESSAGE:
            # respond for Message
            if res is None or len(res) == 0:
                res = ok_body
            else:
                res = Data(buffer=res)
            # pack MessageRespond
            mtp = Package.new(data_type=DataType.MESSAGE_RESPONSE, sn=head.sn, body_length=res.size, body=res)
            return MTPShip(mtp=mtp)
        elif res is not None and len(res) > 0:
            # pack as new Message and put into waiting queue
            return self.pack(payload=res, priority=StarShip.SLOWER)

    # Override
    def remove_linked_ship(self, income: Ship):
        assert isinstance(income, MTPShip), 'income ship error: %s' % income
        if income.mtp.head.data_type == DataType.MESSAGE_RESPONSE:
            super().remove_linked_ship(income=income)

    # Override
    def get_outgo_ship(self, income: Optional[Ship] = None) -> Optional[StarShip]:
        outgo = super().get_outgo_ship(income=income)
        if income is None and isinstance(outgo, MTPShip):
            # if retries == 0, means this ship is first time to be sent,
            # and it would be removed from the dock.
            if outgo.retries == 0 and outgo.mtp.head.data_type == DataType.MESSAGE:
                # put back for waiting response
                self.gate.park_ship(ship=outgo)
        return outgo

    # Override
    # noinspection PyMethodMayBeStatic
    def get_heartbeat(self) -> Optional[StarShip]:
        mtp = Package.new(data_type=DataType.COMMAND, body_length=ping_body.size, body=ping_body)
        return MTPShip(mtp=mtp, priority=StarShip.SLOWER)


#
#  const
#

ping_body = Data(buffer=b'PING')
pong_body = Data(buffer=b'PONG')
again_body = Data(buffer=b'AGAIN')
ok_body = Data(buffer=b'OK')
