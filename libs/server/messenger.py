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

from typing import Optional

from dimp import ID, User
from dimp import Content, TextContent
from dimp import InstantMessage, ReliableMessage
from dimsdk import Session

from ..common import CommonMessenger

from .session import SessionServer
from .dispatcher import Dispatcher
from .filter import Filter


class ServerMessenger(CommonMessenger):

    def __init__(self):
        super().__init__()
        self.dispatcher: Dispatcher = None
        self.__filter: Filter = None
        self.__session: Session = None

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

    #
    #   Message
    #
    def save_message(self, msg: InstantMessage) -> bool:
        # TODO: save instant message
        return True

    def broadcast_message(self, msg: ReliableMessage) -> Optional[Content]:
        """ Deliver message to everyone@everywhere, including all neighbours """
        res = self.filter.check_broadcast(msg=msg)
        if res is not None:
            # broadcast is not allowed
            return res
        # TODO: broadcast this message
        text = 'Message broadcast to "%s" is not implemented' % msg.envelope.receiver
        res = TextContent.new(text=text)
        res.group = msg.envelope.group
        return res

    def deliver_message(self, msg: ReliableMessage) -> Optional[Content]:
        """ Deliver message to the receiver, or broadcast to neighbours """
        res = self.filter.check_deliver(msg=msg)
        if res is not None:
            # deliver is not allowed
            return res
        # call dispatcher to deliver this message
        return self.dispatcher.deliver(msg=msg)

    def forward_message(self, msg: ReliableMessage) -> Optional[Content]:
        """ Re-pack and deliver (Top-Secret) message to the real receiver """
        res = self.filter.check_forward(msg=msg)
        if res is not None:
            # forward is not allowed
            return res
        return super().forward_message(msg=msg)
