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
    Filter
    ~~~~~~

    Filter for delivering message
"""

import weakref
from typing import Optional

from dimp import Envelope, ReliableMessage
from dimp import Content, TextContent
from dimsdk import HandshakeCommand

from ..common import Database, CommonFacebook

from .session import Session
from .messenger import ServerMessenger


g_facebook = CommonFacebook()
g_database = Database()


class Filter:

    def __init__(self, messenger: ServerMessenger):
        super().__init__()
        self.__messenger = weakref.ref(messenger)

    @property
    def messenger(self) -> ServerMessenger:
        return self.__messenger()

    @property
    def facebook(self) -> CommonFacebook:
        return g_facebook

    @property
    def database(self) -> Database:
        return g_database

    #
    #   check
    #
    def __check_blocked(self, envelope: Envelope) -> Optional[Content]:
        sender = envelope.sender
        receiver = envelope.receiver
        group = envelope.group
        # check block-list
        if self.database.is_blocked(sender=sender, receiver=receiver, group=group):
            nickname = self.facebook.name(identifier=receiver)
            if group is None:
                text = 'Message is blocked by %s' % nickname
            else:
                grp_name = self.facebook.name(identifier=group)
                text = 'Message is blocked by %s in group %s' % (nickname, grp_name)
            # response
            res = TextContent(text=text)
            res.group = group
            return res

    def __check_login(self, envelope: Envelope) -> Optional[Content]:
        # check remote user
        user = self.messenger.remote_user
        # TODO: check neighbour stations
        # assert user is not None, 'check client for sending message after handshake accepted'
        if user is None:
            # FIXME: make sure the client sends message after handshake accepted
            sender = envelope.sender
        else:
            sender = user.identifier
        session = self.messenger.current_session(identifier=sender)
        assert isinstance(session, Session), 'session error: %s' % session
        if session.identifier is None:
            return HandshakeCommand.ask(session=session.key)

    #
    #   filters
    #
    def check_deliver(self, msg: ReliableMessage) -> Optional[Content]:
        res = self.__check_login(envelope=msg.envelope)
        if res is not None:
            # session invalid
            return res
        res = self.__check_blocked(envelope=msg.envelope)
        if res is not None:
            # blocked
            return res
