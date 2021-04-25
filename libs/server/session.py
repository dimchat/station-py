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

import threading
import time
import weakref
from weakref import WeakValueDictionary
from typing import Optional, Dict, Set, List

from dimp import hex_encode
from dimp import ID, ReliableMessage
from dimsdk import Messenger, Callback
from dimsdk.plugins.aes import random_bytes

from ..utils import Singleton
from ..stargate import GateDelegate
from ..common import Database


g_database = Database()


def generate_session_key() -> str:
    return hex_encode(random_bytes(32))


class MessageWrapper(GateDelegate, Callback):

    EXPIRES = 600  # 10 minutes

    def __init__(self, msg: ReliableMessage):
        super().__init__()
        self.__time = 0
        self.__msg = msg

    @property
    def msg(self) -> Optional[ReliableMessage]:
        return self.__msg

    @property
    def time(self) -> int:
        """ Get last sent time """
        return self.__time

    @property
    def expired(self) -> bool:
        """ Check whether expired """
        delta = int(time.time()) - self.__time
        return delta > self.EXPIRES

    #
    #   GateDelegate
    #
    def gate_sent(self, gate, payload: bytes, error: Optional[OSError] = None):
        if error is None:
            # success, remove message
            self.__msg = None
        else:
            # failed, force to expired
            self.__time = -1

    #
    #   Callback
    #
    def finished(self, result, error=None):
        if error is None:
            # this message was assigned to the Worker of StarGate,
            # update sent time
            self.__time = int(time.time())


class Session(threading.Thread):

    def __init__(self, client_address: tuple, messenger: Messenger):
        super().__init__()
        self.__key = generate_session_key()
        self.__address = client_address
        self.__messenger = weakref.ref(messenger)
        self.__identifier = None
        self.__active = False
        self.__running = False
        # message queue
        self.__queue: List[MessageWrapper] = []
        self.__lock = threading.Lock()

    def __str__(self):
        clazz = self.__class__.__name__
        return '<%s:%s %s|%s active=%d />' % (clazz, self.__key,
                                              self.__address, self.__identifier,
                                              self.__active)

    def __del__(self):
        # store stranded messages
        self.flush()

    def flush(self):
        # store all message
        wrapper = self.__pop()
        while wrapper is not None:
            msg = wrapper.msg
            if msg is not None:
                g_database.store_message(msg=msg)
            wrapper = self.__pop()

    @property
    def key(self) -> str:
        return self.__key

    @property
    def client_address(self) -> tuple:
        """ (IP, port) """
        return self.__address

    @property
    def messenger(self) -> Optional[Messenger]:
        """ Messenger for pushing message """
        return self.__messenger()

    @property
    def identifier(self) -> Optional[ID]:
        return self.__identifier

    @identifier.setter
    def identifier(self, value: ID):
        self.__identifier = value

    @property
    def active(self) -> bool:
        """ when the client entered background, it should be set to False """
        return self.__active

    @active.setter
    def active(self, value: bool):
        starting = False
        with self.__lock:
            if value != self.__active:
                self.__active = value
                starting = value
        if starting:
            self.start()

    def start(self):
        count = 0
        while self.__running:
            # waiting for last run loop exit
            time.sleep(0.1)
            count += 1
            if count > 100:
                # timeout (10 seconds)
                break
        if not self.__running:
            super().start()

    def run(self):
        self.__running = True
        while self.__active:
            self.__clean()
            # get next message
            wrapper = self.__next()
            if wrapper is None:
                # no more new message
                time.sleep(0.1)
                continue
            msg = wrapper.msg
            if msg is not None:
                # try to push
                if self.messenger.send_message(msg=wrapper.msg, callback=wrapper):
                    time.sleep(0.01)
                else:
                    time.sleep(0.5)
        # save unsent messages
        self.flush()
        self.__running = False

    def push_message(self, msg: ReliableMessage) -> bool:
        """ Push message when session active """
        with self.__lock:
            if self.__active:
                wrapper = MessageWrapper(msg=msg)
                self.__queue.append(wrapper)
                return True

    def __pop(self) -> Optional[MessageWrapper]:
        with self.__lock:
            if len(self.__queue) > 0:
                return self.__queue.pop(0)

    def __next(self) -> Optional[MessageWrapper]:
        with self.__lock:
            for index, wrapper in enumerate(self.__queue):
                if wrapper.time == 0:
                    return wrapper

    def __clean(self):
        with self.__lock:
            index = len(self.__queue) - 1
            while index >= 0:
                wrapper = self.__queue[index]
                if wrapper.msg is None:
                    # message sent
                    self.__queue.pop(index)
                if wrapper.time == -1:
                    # task failed
                    if g_database.store_message(wrapper.msg):
                        self.__queue.pop(index)
                index -= 1


@Singleton
class SessionServer:

    def __init__(self):
        super().__init__()
        # memory cache
        self.__client_addresses: Dict[ID, Set[tuple]] = {}  # {identifier, [client_address]}
        self.__sessions = WeakValueDictionary()             # {client_address, session}

    def get_session(self, client_address: tuple, messenger: Optional[Messenger] = None) -> Session:
        """ Session factory """
        session = self.__sessions.get(client_address)
        if session is None and messenger is not None:
            # create a new session and cache it
            session = Session(client_address=client_address, messenger=messenger)
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
        if identifier is not None:
            # 1. remove client_address with ID
            self.__remove(client_address=address, identifier=identifier)
        # 2. remove session with client_address
        session.active = False
        self.__sessions.pop(address, None)

    def all_sessions(self, identifier: ID) -> Set[Session]:
        """ Get all sessions of this user """
        results = set()
        # 1. get all client_address with ID
        array = self.__client_addresses.get(identifier)
        if array is not None:
            array = array.copy()
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
