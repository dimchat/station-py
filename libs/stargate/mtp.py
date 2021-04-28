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

from dmtp.mtp.tlv import Data
from dmtp.mtp import Package, Header
from dmtp.mtp import Command as MTPCommand, CommandRespond as MTPCommandRespond
from dmtp.mtp import MessageFragment as MTPMessageFragment
from dmtp.mtp import Message as MTPMessage, MessageRespond as MTPMessageRespond

from .base import Gate, Ship, StarShip, ShipDelegate
from .dock import Docker


class MTPShip(StarShip):
    """ Star Ship with MTP Package """

    def __init__(self, package: Package, priority: int = 0, delegate: Optional[ShipDelegate] = None):
        super().__init__(priority=priority, delegate=delegate)
        self.__package = package

    @property
    def package(self) -> Package:
        """ Get request will be sent to remote star """
        return self.__package

    # Override
    @property
    def sn(self) -> bytes:
        return self.__package.head.sn.get_bytes()

    # Override
    @property
    def payload(self) -> bytes:
        return self.__package.body.get_bytes()


class MTPDocker(Docker):
    """ Docker for MTP packages """

    def __init__(self, gate: Gate):
        super().__init__(gate=gate)

    @classmethod
    def check(cls, connection: Connection) -> bool:
        # 1. check received data
        buffer = connection.received()
        if buffer is not None:
            data = Data(data=buffer)
            head = Header.parse(data=data)
            return head is not None

    # Override
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[ShipDelegate] = None) -> bool:
        req = Data(data=payload)
        req_pack = Package.new(data_type=MTPMessage, body_length=req.length, body=req)
        req_ship = MTPShip(package=req_pack, priority=priority, delegate=delegate)
        return self.dock.put(ship=req_ship)

    def __receive_package(self) -> Optional[Package]:
        # 1. check received data
        buffer = self._received_buffer()
        if buffer is None:
            # received nothing
            return None
        data = Data(data=buffer)
        head = Header.parse(data=data)
        if head is None:
            # not a MTP package?
            if data.length < 20:
                # wait for more data
                return None
            pos = data.find(sub=Header.MAGIC_CODE, start=1)  # MAGIC_CODE_OFFSET = 0
            if pos > 0:
                # found next head(starts with 'DIM'), skip data before it
                self._receive_buffer(length=pos)
            else:
                # skip the whole data
                self._receive_buffer(length=data.length)
            return None
        # 2. receive data with 'head.length + body.length'
        body_len = head.body_length
        if body_len < 0:
            # should not happen
            body_len = data.length - head.length
        pack_len = head.length + body_len
        if pack_len > data.length:
            # waiting for more data
            return None
        # receive package
        buffer = self._receive_buffer(length=pack_len)
        data = Data(data=buffer)
        body = data.slice(start=head.length)
        return Package(data=data, head=head, body=body)

    # Override
    def _get_income_ship(self) -> Optional[Ship]:
        income = self.__receive_package()
        if income is not None:
            return MTPShip(package=income)

    # Override
    def _handle_ship(self, income: Ship) -> Optional[StarShip]:
        assert isinstance(income, MTPShip), 'income ship error: %s' % income
        pack = income.package
        head = pack.head
        body = pack.body
        # 1. check data type
        data_type = head.data_type
        if data_type == MTPCommand:
            # respond for Command directly
            if body == ping_body:  # 'PING'
                res = pong_body    # 'PONG'
                pack = Package.new(data_type=MTPCommandRespond, sn=head.sn, body_length=res.length, body=res)
                return MTPShip(package=pack, priority=StarShip.SLOWER)
            return None
        elif data_type == MTPCommandRespond:
            # remove linked outgo Ship
            return super()._handle_ship(income=income)
        elif data_type == MTPMessageFragment:
            # just ignore
            return None
        elif data_type == MTPMessageRespond:
            # remove linked outgo Ship
            super()._handle_ship(income=income)
            if body.length == 0 or body == ok_body:
                # just ignore
                return None
            elif body == again_body:
                # TODO: mission failed, send the message again
                return None
        # 2. process payload by delegate
        delegate = self.delegate
        if body.length > 0 and delegate is not None:
            res = delegate.gate_received(gate=self.gate, payload=body.get_bytes())
        else:
            res = None
        # 3. response
        if data_type == MTPMessage:
            # respond for Message
            if res is None or len(res) == 0:
                res = ok_body
            else:
                res = Data(data=res)
            pack = Package.new(data_type=MTPMessageRespond, sn=head.sn, body_length=res.length, body=res)
            return MTPShip(package=pack, priority=StarShip.NORMAL)
        elif res is not None and len(res) > 0:
            # push as new Message
            self.send(payload=res, priority=StarShip.NORMAL)

    # Override
    def _send_ship(self, outgo: StarShip) -> bool:
        assert isinstance(outgo, MTPShip), 'outgo ship error: %s' % outgo
        pack = outgo.package
        # check data type
        if pack.head.data_type == MTPMessage:
            # put back for response
            self.dock.put(ship=outgo)
        # send out request data
        return self._send_buffer(data=pack.get_bytes()) == pack.length

    # Override
    def _get_heartbeat(self) -> Optional[StarShip]:
        pack = Package.new(data_type=MTPCommand, body_length=ping_body.length, body=ping_body)
        return MTPShip(package=pack, priority=StarShip.SLOWER)


#
#  const
#

ping_body = Data(data=b'PING')
pong_body = Data(data=b'PONG')
again_body = Data(data=b'AGAIN')
ok_body = Data(data=b'OK')
