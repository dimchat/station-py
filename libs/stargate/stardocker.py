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
from typing import Optional

from dmtp.mtp.tlv import Data
from dmtp.mtp import Package, Header
from dmtp.mtp import Command as MTPCommand, CommandRespond as MTPCommandRespond
from dmtp.mtp import MessageFragment as MTPMessageFragment
from dmtp.mtp import Message as MTPMessage, MessageRespond as MTPMessageRespond

from .base import Gate, GateDelegate, Worker
from .base import OutgoShip
from .docker import Docker
from .starship import StarShip


ping_body = Data(data='PING')
pong_body = Data(data='PONG')
again_body = Data(data='AGAIN')
ok_body = Data(data='OK')


class StarDocker(Docker):
    """ Docker for MTP packages """

    def __init__(self, gate: Gate, delegate: GateDelegate):
        super().__init__(gate=gate, delegate=delegate)
        # time for checking heartbeat
        self.__heartbeat_expired = int(time.time())

    def __send_package(self, pack: Package) -> int:
        conn = self.current_connection
        if conn is None:
            # connection lost
            return -1
        return conn.send(data=pack.get_bytes())

    def __receive_package(self) -> Optional[Package]:
        conn = self.current_connection
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
            pos = data.find(sub=Header.MAGIC_CODE)
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
    def _process_income(self) -> bool:
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
            if body == ping_body:
                res = pong_body
                pack = Package.new(data_type=MTPCommandRespond, sn=head.sn, body_length=res.length, body=res)
                ship = StarShip(package=pack, priority=OutgoShip.SLOWER)
                self.add_task(ship=ship)
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
            pack = Package.new(data_type=MTPCommandRespond, sn=head.sn, body_length=res.length, body=res)
            ship = StarShip(package=pack, priority=OutgoShip.NORMAL)
            self.add_task(ship=ship)
        else:
            assert data_type == MTPMessageRespond, 'data type error: %s' % data_type
            # process Message Respond
            sn = head.sn.get_bytes()
            ship = self._pop_waiting(sn=sn)
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
        # received data in the Message Respond
        if body.length > 0:
            delegate = self.delegate
            if delegate is not None:
                delegate.gate_received(gate=self.gate, payload=body.get_bytes())
        # float control
        if Worker.INCOME_INTERVAL > 0:
            time.sleep(Worker.INCOME_INTERVAL)
        return True

    # Override
    def _process_outgo(self) -> bool:
        ship = self.dock.pop()
        if ship is None:
            # no more task now
            ship = self._get_waiting()
            if ship is None:
                # no task expired now
                return False
        assert isinstance(ship, StarShip), 'outgo ship error: %s' % ship
        outgo = ship.package
        head = outgo.head
        # check data type
        data_type = head.data_type
        if data_type == MTPMessage:
            # set for callback when received response
            sn = head.sn.get_bytes()
            self._set_waiting(sn=sn, ship=ship)
        # send out request data
        res = self.__send_package(pack=outgo)
        if res != outgo.length:
            # callback for sent failed
            delegate = ship.delegate
            if delegate is None:
                delegate = self.delegate
            if delegate is not None:
                error = ConnectionError('Socket error')
                delegate.gate_sent(gate=self.gate, payload=ship.payload, error=error)
        # flow control
        if Worker.OUTGO_INTERVAL > 0:
            time.sleep(Worker.OUTGO_INTERVAL)
        return True

    # Override
    def _process_heartbeat(self):
        # check time for next heartbeat
        now = time.time()
        if now > self.__heartbeat_expired:
            conn = self.current_connection
            if conn.is_expired(now=now):
                req = ping_body
                pack = Package.new(data_type=MTPCommandRespond, body_length=req.length, body=req)
                ship = StarShip(package=pack, priority=OutgoShip.SLOWER)
                self.add_task(ship=ship)
            # try heartbeat next 2 seconds
            self.__heartbeat_expired = now + 2
        # idling
        assert Worker.IDLE_INTERVAL > 0, 'IDLE_INTERVAL error'
        time.sleep(Worker.IDLE_INTERVAL)
