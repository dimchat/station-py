# -*- coding: utf-8 -*-
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
    Messenger for request handler in station
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

import time
from typing import List

from dimp import ID, EVERYWHERE, User
from dimp import Envelope, InstantMessage
from dimp import Content, Command, MetaCommand, DocumentCommand, GroupCommand
from dimp import Processor
from dimsdk import MessageTransmitter

from libs.utils import NotificationCenter
from libs.common import NotificationNames
from libs.common import CommonMessenger

from .session import Session, SessionServer
from .dispatcher import Dispatcher
from .filter import Filter
from .facebook import ServerFacebook


class ServerMessenger(CommonMessenger):

    EXPIRES = 3600  # query expires (1 hour)

    def __init__(self):
        super().__init__()
        self.__filter: Filter = None
        self.__session: Session = None
        # for checking duplicated queries
        self.__meta_queries = {}     # ID -> time
        self.__profile_queries = {}  # ID -> time
        self.__group_queries = {}    # ID -> time

    def _create_facebook(self) -> ServerFacebook:
        return ServerFacebook()

    def _create_processor(self) -> Processor:
        from .processor import ServerProcessor
        return ServerProcessor(messenger=self)

    def _create_transmitter(self) -> MessageTransmitter:
        from .transmitter import ServerTransmitter
        return ServerTransmitter(messenger=self)

    @property
    def dispatcher(self) -> Dispatcher:
        return Dispatcher()

    @property
    def filter(self) -> Filter:
        if self.__filter is None:
            self.__filter = Filter(messenger=self)
        return self.__filter

    @filter.setter
    def filter(self, value: Filter):
        self.__filter = value

    #
    #   Session
    #
    @property
    def session_server(self) -> SessionServer:
        return SessionServer()

    def current_session(self, identifier: ID) -> Session:
        session = self.__session
        # if identifier is None:
        #     user = self.remote_user
        #     if user is None:
        #         # FIXME: remote user not login?
        #         return session
        #     else:
        #         identifier = user.identifier
        if session is not None:
            # check whether the current session's identifier matched
            if session.identifier == identifier:
                # current session belongs to the same user
                return session
            # TODO: user switched, clear session?
        # get new session with identifier
        address = self.remote_address
        assert address is not None, 'client address not found: %s' % identifier
        session = self.session_server.get_session(client_address=address)
        self.__session = session
        return session

    #
    #   Remote user
    #
    @property
    def remote_user(self) -> User:
        return self.get_context(key='remote_user')

    @property
    def remote_address(self):  # (IP, port)
        return self.get_context(key='remote_address')

    #
    #   HandshakeDelegate
    #
    def handshake_accepted(self, session: Session):
        self.session_server.insert_session(session=session)
        sender = session.identifier
        session_key = session.key
        client_address = session.client_address
        user = self.facebook.user(identifier=sender)
        self.context['remote_user'] = user
        self.info('handshake accepted %s %s, %s' % (client_address, sender, session_key))
        # post notification: USER_LOGIN
        NotificationCenter().post(name=NotificationNames.USER_LOGIN, sender=self, info={
            'ID': sender,
            'client_address': client_address,
        })

    #
    #   Command
    #
    def __send_command(self, cmd: Command) -> bool:
        everyone = ID.create(name='station', address=EVERYWHERE)
        return self.__send_content(content=cmd, receiver=everyone)

    def __send_content(self, content: Content, receiver: ID) -> bool:
        station = self.get_context(key='station')
        if station is None:
            user = self.facebook.current_user
            if user is None:
                return False
            sender = user.identifier
        else:
            sender = station.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        s_msg = self.encrypt_message(msg=i_msg)
        if s_msg is None:
            # failed to encrypt message
            return False
        r_msg = self.sign_message(msg=s_msg)
        assert r_msg is not None, 'failed to sign message: %s' % s_msg
        r_msg.delegate = self
        self.dispatcher.deliver(msg=r_msg)
        return True

    def query_meta(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__meta_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__meta_queries[identifier] = now
        # query from DIM network
        cmd = MetaCommand(identifier=identifier)
        return self.__send_command(cmd=cmd)

    def query_profile(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__profile_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__profile_queries[identifier] = now
        # query from DIM network
        cmd = DocumentCommand(identifier=identifier)
        return self.__send_command(cmd=cmd)

    # FIXME: separate checking for querying each user
    def query_group(self, group: ID, users: List[ID]) -> bool:
        now = time.time()
        last = self.__group_queries.get(group, 0)
        if (now - last) < self.EXPIRES:
            return False
        if len(users) == 0:
            return False
        self.__group_queries[group] = now
        # query from users
        cmd = GroupCommand.query(group=group)
        checking = False
        for item in users:
            if self.__send_content(content=cmd, receiver=item):
                checking = True
        return checking
