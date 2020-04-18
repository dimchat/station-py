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
from typing import Optional, Union

from dimp import ID, EVERYWHERE, User
from dimp import InstantMessage, ReliableMessage
from dimp import Content, Command, MetaCommand, ProfileCommand, GroupCommand

from libs.common import CommonMessenger

from .session import Session, SessionServer
from .dispatcher import Dispatcher
from .filter import Filter


class ServerMessenger(CommonMessenger):

    EXPIRES = 3600  # query expires (1 hour)

    def __init__(self):
        super().__init__()
        self.dispatcher: Dispatcher = None
        self.__filter: Filter = None
        self.__session: Session = None
        # for checking duplicated queries
        self.__meta_queries = {}     # ID -> time
        self.__profile_queries = {}  # ID -> time
        self.__group_queries = {}    # ID -> time

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
        return self.get_context(key='session_server')

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
        session = self.session_server.new(identifier=identifier, client_address=address)
        self.__session = session
        return session

    #
    #   Remote user
    #
    @property
    def remote_user(self) -> User:
        return self.get_context(key='remote_user')

    @remote_user.setter
    def remote_user(self, value: User):
        self.set_context(key='remote_user', value=value)

    @property
    def remote_address(self):  # (IP, port)
        return self.get_context(key='remote_address')

    @remote_address.setter
    def remote_address(self, value):
        self.set_context(key='remote_address', value=value)

    # Override
    def process_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        receiver = self.facebook.identifier(string=msg.envelope.receiver)
        if receiver.is_group:
            # deliver group message
            res = self.__deliver_message(msg=msg)
            if receiver.is_broadcast:
                # if this is a broadcast, deliver it, send back the response
                # and continue to process it with the station.
                # because this station is also a recipient too.
                if res is not None:
                    self.send_message(msg=res, callback=None, split=False)
            else:
                # or, this is is an ordinary group message,
                # just deliver it to the group assistant
                # and return the response to the sender.
                return res
        # try to decrypt and process message
        try:
            return super().process_message(msg=msg)
        except LookupError as error:
            if str(error).startswith('receiver error'):
                # not mine? deliver it
                return self.__deliver_message(msg=msg)
            else:
                raise error

    def __deliver_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        """ Deliver message to the receiver, or broadcast to neighbours """
        s_msg = self.verify_message(msg=msg)
        if s_msg is None:
            # signature error?
            return None
        # FIXME: check deliver permission
        res = None  # self.filter.check_deliver(msg=msg)
        if res is None:
            # delivering is allowed, call dispatcher to deliver this message
            res = self.dispatcher.deliver(msg=msg)
        # pack response
        if res is not None:
            user = self.facebook.current_user
            sender = user.identifier
            receiver = msg.envelope.sender
            i_msg = InstantMessage.new(content=res, sender=sender, receiver=receiver)
            s_msg = self.encrypt_message(msg=i_msg)
            return self.sign_message(msg=s_msg)

    #
    #   Command
    #
    def __send_command(self, cmd: Command) -> bool:
        everyone = ID.new(name='station', address=EVERYWHERE)
        return self.__send_content(content=cmd, receiver=everyone)

    def __send_content(self, content: Content, receiver: ID) -> bool:
        station = self.get_context('station')
        if station is None:
            sender = self.facebook.current_user.identifier
        else:
            sender = station.identifier
        i_msg = InstantMessage.new(content=content, sender=sender, receiver=receiver)
        s_msg = self.encrypt_message(msg=i_msg)
        if s_msg is None:
            # failed to encrypt message
            return False
        r_msg = self.sign_message(msg=s_msg)
        assert r_msg is not None, 'failed to sign message: %s' % s_msg
        self.dispatcher.deliver(msg=r_msg)
        return True

    def query_meta(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__meta_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__meta_queries[identifier] = now
        # query from DIM network
        cmd = MetaCommand.new(identifier=identifier)
        return self.__send_command(cmd=cmd)

    def query_profile(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__profile_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__profile_queries[identifier] = now
        # query from DIM network
        cmd = ProfileCommand.new(identifier=identifier)
        return self.__send_command(cmd=cmd)

    # FIXME: separate checking for querying each user
    def query_group(self, group: ID, users: list) -> bool:
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

    #
    #   Message
    #
    def save_message(self, msg: InstantMessage) -> bool:
        # TODO: save instant message
        return True

    def suspend_message(self, msg: Union[ReliableMessage, InstantMessage]):
        if isinstance(msg, ReliableMessage):
            # TODO: save this message in a queue waiting sender's meta response
            pass
        elif isinstance(msg, InstantMessage):
            # TODO: save this message in a queue waiting receiver's meta response
            pass
