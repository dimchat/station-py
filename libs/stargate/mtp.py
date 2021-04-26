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

from dmtp.mtp.tlv import Data
from dmtp.mtp import Package, Header
from dmtp.mtp import Command as MTPCommand, CommandRespond as MTPCommandRespond
from dmtp.mtp import MessageFragment as MTPMessageFragment
from dmtp.mtp import Message as MTPMessage, MessageRespond as MTPMessageRespond

from .base import Gate, GateDelegate
from .base import OutgoShip
from .dock import Docker


class MTPShip(OutgoShip):
    """ Star Ship with MTP Package """

    def __init__(self, package: Package, priority: int = 0, delegate: Optional[GateDelegate] = None):
        super().__init__()
        self.__package = package
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
    def package(self) -> Package:
        """ Get request will be sent to remote star """
        return self.__package

    # Override
    @property
    def sn(self) -> bytes:
        return self.package.head.sn.get_bytes()

    # Override
    @property
    def payload(self) -> bytes:
        return self.package.body.get_bytes()


class MTPDocker(Docker):
    """ Docker for MTP packages """

    def __init__(self, gate: Gate):
        super().__init__(gate=gate)
        # time for checking heartbeat
        self.__heartbeat_expired = int(time.time())

    @classmethod
    def check(cls, connection: Connection) -> bool:
        # 1. check received data
        buffer = connection.received()
        if buffer is not None:
            data = Data(data=buffer)
            head = Header.parse(data=data)
            return head is not None

    # Override
    def send(self, payload: bytes, priority: int = 0, delegate: Optional[GateDelegate] = None) -> bool:
        req = Data(data=payload)
        req_pack = Package.new(data_type=MTPMessage, body_length=req.length, body=req)
        req_ship = MTPShip(package=req_pack, priority=priority, delegate=delegate)
        return self.dock.put(ship=req_ship)

    def __send_package(self, pack: Package) -> int:
        conn = self.connection
        if conn is None:
            # connection lost
            return -1
        return conn.send(data=pack.get_bytes())

    def __receive_package(self) -> Optional[Package]:
        conn = self.connection
        if conn is None:
            # connection lost
            return None
        # 1. check received data
        buffer = conn.received()
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
                conn.receive(length=pos)
            else:
                # skip the whole data
                conn.receive(length=data.length)
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
        buffer = conn.receive(length=pack_len)
        data = Data(data=buffer)
        body = data.slice(start=head.length)
        return Package(data=data, head=head, body=body)

    # Override
    def _handle_income(self) -> bool:
        income = self.__receive_package()
        if income is None:
            # no more package now
            return False
        head = income.head
        body = income.body
        # check data type
        data_type = head.data_type
        if data_type == MTPCommand:
            # respond for Command
            if body == ping_body:  # b'PING'
                res = pong_body    # b'PONG'
                res_pack = Package.new(data_type=MTPCommandRespond, sn=head.sn, body_length=res.length, body=res)
                res_ship = MTPShip(package=res_pack, priority=OutgoShip.SLOWER)
                self.dock.put(ship=res_ship)
            return True
        elif data_type == MTPCommandRespond:
            # just ignore
            return True
        elif data_type == MTPMessageFragment:
            # just ignore
            return True
        elif data_type == MTPMessage:
            # respond for Message
            res = ok_body
            res_pack = Package.new(data_type=MTPMessageRespond, sn=head.sn, body_length=res.length, body=res)
            res_ship = MTPShip(package=res_pack, priority=OutgoShip.NORMAL)
            self.dock.put(ship=res_ship)
        else:
            assert data_type == MTPMessageRespond, 'data type error: %s' % data_type
            # process Message Respond
            sn = head.sn.get_bytes()
            ship = self.dock.pop(sn=sn)
            if ship is not None:
                delegate = ship.delegate
                if delegate is not None:
                    # callback for the request data
                    if body == again_body:
                        error = ConnectionResetError('Send the message again')
                    else:
                        error = None
                    delegate.gate_sent(gate=self.gate, payload=ship.payload, error=error)
            # check body
            if body == ok_body:
                # just ignore
                return True
            elif body == again_body:
                # TODO: mission failed, send the message again
                return True
            elif body == pong_body:
                # FIXME: should not happen
                return True
        # received data in the Message Respond
        if body.length > 0:
            delegate = self.delegate
            if delegate is not None:
                res = delegate.gate_received(gate=self.gate, payload=body.get_bytes())
                if res is not None:
                    self.send(payload=res, priority=OutgoShip.NORMAL)
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
        assert isinstance(ship, MTPShip), 'outgo ship error: %s' % ship
        outgo = ship.package
        # check data type
        if outgo.head.data_type == MTPMessage:
            # put back for response
            self.dock.put(ship=ship)
        # send out request data
        res = self.__send_package(pack=outgo)
        if res != outgo.length:
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
                req = ping_body
                pack = Package.new(data_type=MTPCommand, body_length=req.length, body=req)
                ship = MTPShip(package=pack, priority=OutgoShip.SLOWER)
                self.dock.put(ship=ship)
            # try heartbeat next 2 seconds
            self.__heartbeat_expired = now + 2
        # idling
        assert Gate.IDLE_INTERVAL > 0, 'IDLE_INTERVAL error'
        time.sleep(Gate.IDLE_INTERVAL)


#
#  const
#

ping_body = Data(data=b'PING')
pong_body = Data(data=b'PONG')
again_body = Data(data=b'AGAIN')
ok_body = Data(data=b'OK')
