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

    for user connection
"""

import threading
import weakref
from typing import MutableMapping, MutableSet
from typing import Optional, Dict, Set

from dimp import ID

from ..utils import Singleton

from .session import Session


@Singleton
class SessionServer:

    def __init__(self):
        super().__init__()
        # memory cache
        self.__client_addresses: Dict[ID, MutableSet[tuple]] = {}
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
                removed = set()
                for address in all_addresses:
                    session = self.__sessions.get(address)
                    if session is None:
                        removed.add(address)
                    elif session.active:
                        sessions.add(session)
                for address in removed:
                    all_addresses.discard(address)
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

    def update_session(self, session: Session, identifier: ID):
        """ Update ID in this session """
        address = session.client_address
        assert address is not None, 'session error: %s' % session
        old = session.identifier
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
