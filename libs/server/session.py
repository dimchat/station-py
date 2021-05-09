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
from weakref import WeakValueDictionary
from typing import Optional, Dict, Set

from dimp import hex_encode
from dimp import ID
from dimsdk.plugins.aes import random_bytes

from ..utils import Singleton
from ..common import Database
from ..common import BaseSession
from ..common import CommonMessenger


g_database = Database()


def generate_session_key() -> str:
    return hex_encode(random_bytes(32))


class Session(BaseSession):

    def __init__(self, messenger: CommonMessenger, sock: socket.socket):
        super().__init__(messenger=messenger, sock=sock)
        self.__client_address = sock.getpeername()
        self.__key = generate_session_key()
        self.__identifier = None

    def __str__(self):
        clazz = self.__class__.__name__
        return '<%s:%s %s|%s active=%d />' % (clazz, self.key,
                                              self.client_address, self.identifier,
                                              self.active)

    @property
    def client_address(self) -> tuple:
        """ (IP, port) """
        return self.__client_address

    @property
    def key(self) -> str:
        return self.__key

    @property
    def identifier(self) -> Optional[ID]:
        return self.__identifier

    @identifier.setter
    def identifier(self, value: ID):
        self.__identifier = value

    @property
    def active(self) -> bool:
        return super().active

    @active.setter
    def active(self, value: bool):
        old = self.active
        BaseSession.active.__set__(self, value)
        if old != value and value:
            identifier = self.identifier
            if identifier is not None:
                self.__scan(identifier=identifier)

    def __scan(self, identifier: ID):
        self.debug('scanning messages for: %s' % identifier)
        messages = g_database.fetch_all_messages(receiver=identifier)
        total = len(messages)
        self.info('%d message(s) loaded for: %s' % (total, identifier))
        success = 0
        for msg in messages:
            if self.push_message(msg=msg):
                success += 1
            else:
                g_database.store_message(msg=msg)
        self.info('%d/%d message(s) pushed to %s' % (success, total, identifier))


@Singleton
class SessionServer:

    def __init__(self):
        super().__init__()
        # memory cache
        self.__client_addresses: Dict[ID, Set[tuple]] = {}  # {identifier, [client_address]}
        self.__sessions = WeakValueDictionary()             # {client_address, session}
        self.__lock = threading.Lock()

    def get_session(self, client_address: tuple,
                    messenger: Optional[CommonMessenger] = None,
                    sock: Optional[socket.socket] = None) -> Optional[Session]:
        """ Session factory """
        with self.__lock:
            session = self.__sessions.get(client_address)
            if session is None and messenger is not None and sock is not None:
                # create a new session and cache it
                session = Session(messenger=messenger, sock=sock)
                self.__sessions[client_address] = session
            return session

    def __insert(self, client_address: tuple, identifier: ID):
        array = self.__client_addresses.get(identifier)
        if array is None:
            array = set()
            self.__client_addresses[identifier] = array
        array.add(client_address)

    def __remove(self, client_address: tuple, identifier: ID):
        array = self.__client_addresses.get(identifier)
        if array is not None:
            array.discard(client_address)
            if len(array) == 0:
                # all sessions removed
                self.__client_addresses.pop(identifier)

    def update_session(self, session: Session, identifier: ID):
        """ Insert a session with ID into memory cache """
        address = session.client_address
        assert address is not None, 'session error: %s' % session
        old = session.identifier
        with self.__lock:
            if old is not None:
                # 0. remove client_address from old ID
                self.__remove(client_address=address, identifier=old)
            # 1. insert client_address for new ID
            self.__insert(client_address=address, identifier=identifier)
        # 2. update session ID
        session.identifier = identifier

    def remove_session(self, session: Session):
        """ Remove the session from memory cache """
        identifier = session.identifier
        address = session.client_address
        assert address is not None, 'session error: %s' % session
        with self.__lock:
            if identifier is not None:
                # 1. remove client_address with ID
                self.__remove(client_address=address, identifier=identifier)
            # 2. remove session with client_address
            self.__sessions.pop(address, None)
        session.active = False

    def all_sessions(self, identifier: ID) -> Set[Session]:
        """ Get all sessions of this user """
        results = set()
        with self.__lock:
            # 1. get all client_address with ID
            array = self.__client_addresses.get(identifier, set())
            # 2. get session by each client_address
            for item in array:
                session = self.__sessions.get(item)
                if session is not None:
                    results.add(session)
        return results

    def active_sessions(self, identifier: ID) -> Set[Session]:
        results = set()
        # 1. get all sessions
        array = self.all_sessions(identifier=identifier)
        for item in array:
            # 2. check session active
            if item.active:
                results.add(item)
        return results

    #
    #   Users
    #
    def all_users(self) -> Set[ID]:
        """ Get all users """
        return set(self.__client_addresses.keys())

    def is_active(self, identifier: ID) -> bool:
        """ Check whether user has active session """
        sessions = self.all_sessions(identifier=identifier)
        for item in sessions:
            if item.active:
                return True

    def active_users(self, start: int, limit: int) -> Set[ID]:
        """ Get active users """
        users = set()
        array = self.all_users()
        if limit > 0:
            end = start + limit
        else:
            end = 1024
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
