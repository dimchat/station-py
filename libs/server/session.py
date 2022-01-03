# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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

"""
    Session Server
    ~~~~~~~~~~~~~~

    for login user
"""

import socket
import traceback
from typing import Optional, List

from startrek import GateStatus, Gate
from startrek import Connection, ActiveConnection
from startrek import Arrival

from dimp import hex_encode
from dimp import NetworkType, ID
from dimsdk.plugins.aes import random_bytes

from ..utils import NotificationCenter
from ..network import WSArrival, MarsStreamArrival, MTPStreamArrival
from ..common import NotificationNames
from ..common import BaseSession, CommonMessenger


def generate_session_key() -> str:
    return hex_encode(random_bytes(32))


class Session(BaseSession):

    def __init__(self, messenger: CommonMessenger, address: tuple, sock: socket.socket):
        super().__init__(messenger=messenger, address=address, sock=sock)
        self.__key = generate_session_key()

    @property
    def client_address(self) -> tuple:
        return self.remote_address

    @property
    def key(self) -> str:
        return self.__key

    @property  # Override
    def running(self) -> bool:
        if super().running:
            gate = self.gate
            conn = gate.get_connection(remote=self.remote_address, local=None)
            if conn is not None:
                return conn.opened

    #
    #   GateDelegate
    #

    # Override
    def gate_status_changed(self, previous: GateStatus, current: GateStatus,
                            remote: tuple, local: Optional[tuple], gate: Gate):
        if current is None or current == GateStatus.ERROR:
            # connection error or session finished
            self.active = False
            self.stop()
            NotificationCenter().post(name=NotificationNames.DISCONNECTED, sender=self, info={
                'session': self,
            })
        elif current == GateStatus.READY:
            # connected/reconnected
            NotificationCenter().post(name=NotificationNames.CONNECTED, sender=self, info={
                'session': self,
            })

    # Override
    def gate_received(self, ship: Arrival,
                      source: tuple, destination: Optional[tuple], connection: Connection):
        if isinstance(ship, MTPStreamArrival):
            payload = ship.payload
        elif isinstance(ship, MarsStreamArrival):
            payload = ship.payload
        elif isinstance(ship, WSArrival):
            payload = ship.payload
        else:
            raise ValueError('unknown arrival ship: %s' % ship)
        # check payload
        if len(payload) == 0:
            packages = []
        elif payload.startswith(b'{'):
            # JsON in lines
            packages = payload.splitlines()
        else:
            packages = [payload]
        array = []
        for pack in packages:
            try:
                responses = self.__process_package(data=pack)
                for res in responses:
                    if res is None or len(res) == 0:
                        # should not happen
                        continue
                    array.append(res)
            except Exception as error:
                self.error('parse message failed (%s): %s, %s' % (source, error, pack))
                self.error('payload: %s' % payload)
                traceback.print_exc()
                # from dimsdk import TextContent
                # return TextContent.new(text='parse message failed: %s' % error)
        gate = self.gate
        if len(array) == 0:
            if connection is not None and not isinstance(connection, ActiveConnection):
                # station MUST respond something to client request (Tencent Mars)
                gate.send_response(payload=b'', ship=ship, remote=source, local=destination)
        else:
            for item in array:
                gate.send_response(payload=item, ship=ship, remote=source, local=destination)

    def __process_package(self, data: bytes) -> List[bytes]:
        messenger = self.messenger
        r_msg = messenger.deserialize_message(data=data)
        if not self.__trusted_sender(sender=r_msg.sender):
            s_msg = messenger.verify_message(msg=r_msg)
            if s_msg is None:
                self.error(msg='failed to verify message: %s' % r_msg)
                return []
        return messenger.process_package(data=data)

    def __trusted_sender(self, sender: ID) -> bool:
        current = self.identifier
        if current is None:
            # not login yet
            return False
        # handshake accepted, check current user with sender
        if current == sender:
            # no need to verify signature of this message
            # which sender is equal to current id in session
            return True
        if current.type == NetworkType.STATION:
            # if it's a roaming message delivered from another neighbor station,
            # shall we trust that neighbor totally and skip verifying too ???
            return True
