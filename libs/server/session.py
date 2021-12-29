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
import threading
import traceback
import weakref
from typing import Optional, Set, Dict, MutableMapping

from startrek import GateStatus, Gate
from startrek import Connection, ActiveConnection
from startrek import Arrival

from dimp import hex_encode
from dimp import ID
from dimsdk.plugins.aes import random_bytes

from ..utils import Singleton
from ..utils import NotificationCenter
from ..network import WSArrival, MarsStreamArrival, MTPStreamArrival
from ..database import Database
from ..common import NotificationNames
from ..common import BaseSession, CommonMessenger


g_database = Database()


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
        if payload.startswith(b'{'):
            # JsON in lines
            packages = payload.splitlines()
        else:
            packages = [payload]
        array = []
        messenger = self.messenger
        for pack in packages:
            try:
                responses = messenger.process_package(data=pack)
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


@Singleton
class SessionServer:

    def __init__(self):
        super().__init__()
        # memory cache
        self.__client_addresses: Dict[ID, Set[tuple]] = {}
        self.__sessions: MutableMapping[tuple, Session] = weakref.WeakValueDictionary()
        self.__lock = threading.Lock()

    def __insert_address(self, identifier: ID, client_address: tuple):
        addresses = self.__client_addresses.get(identifier)
        if addresses is None:
            addresses = set()
            self.__client_addresses[identifier] = addresses
        addresses.add(client_address)

    def __remove_address(self, identifier: ID, client_address: tuple):
        addresses = self.__client_addresses.get(identifier)
        if addresses is not None:
            addresses.discard(client_address)
            if len(addresses) == 0:
                self.__client_addresses.pop(identifier)

    def active_sessions(self, identifier: ID) -> Set[Session]:
        """ Get all active sessions with user ID """
        sessions: Set[Session] = set()
        with self.__lock:
            # 1. get all client addresses with ID
            all_addresses = self.__client_addresses.get(identifier)
            if all_addresses is not None:
                # 2. get sessions by each address
                for address in all_addresses:
                    session = self.__sessions.get(address)
                    if session is not None and session.active:
                        sessions.add(session)
        return sessions

    def get_session(self, address: tuple) -> Optional[Session]:
        """ Get session by client address """
        with self.__lock:
            return self.__sessions.get(address)

    def add_session(self, session: Session):
        """ Cache session with client address """
        address = session.client_address
        assert address is not None, 'session error: %s' % session
        assert session.identifier is None, 'session error: %s' % session
        with self.__lock:
            self.__sessions[address] = session
        return True

    def update_session(self, session: Session, identifier: ID = None):
        """ Update ID in this session """
        address = session.client_address
        assert address is not None, 'session error: %s' % session
        old = session.identifier
        if identifier is None:
            if old is not None:
                g_database.renew_session(address=address, identifier=old)
            return False
        if old == identifier:
            # nothing changed
            return False
        with self.__lock:
            if old is not None:
                # 0. remove client address from old ID
                self.__remove_address(identifier=old, client_address=address)
            # 1. insert remote address for new ID
            self.__insert_address(identifier=identifier, client_address=address)
        # 2. update session ID
        session.identifier = identifier
        return True

    def remove_session(self, session: Session):
        """ Remove the session """
        identifier = session.identifier
        address = session.client_address
        assert address is not None, 'session error: %s' % session
        with self.__lock:
            # 1. remove session with client address
            self.__sessions.pop(address, None)
            # 2. remove client address with ID if exists
            if identifier is not None:
                self.__remove_address(identifier=identifier, client_address=address)
        # 3. set inactive
        session.active = False
        return True

    #
    #   Users
    #
    def all_users(self) -> Set[ID]:
        """ Get all users """
        with self.__lock:
            return set(self.__client_addresses.keys())

    def is_active(self, identifier: ID) -> bool:
        """ Check whether user has active session """
        sessions = self.active_sessions(identifier=identifier)
        return len(sessions) > 0

    def active_users(self, start: int, limit: int) -> Set[ID]:
        """ Get active users """
        users = set()
        array = self.all_users()
        if limit > 0:
            end = start + limit
        else:
            end = 10240
        index = -1
        for item in array:
            if self.is_active(identifier=item):
                index += 1
                if index < start:
                    # skip
                    continue
                elif index < end:
                    # OK
                    users.add(item)
                else:
                    # finished
                    break
        return users
