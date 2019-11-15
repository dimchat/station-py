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

from typing import Optional

from dimp import ID
from dimp import Envelope, ReliableMessage
from dimp import Content, TextContent
from dimp import HandshakeCommand
from dimsdk import Session

from ..common import Facebook, Database


class Filter:

    def __init__(self, messenger):
        super().__init__()
        # messenger
        self.__messenger = messenger

    @property
    def messenger(self):  # ServerMessenger
        return self.__messenger

    @property
    def facebook(self) -> Facebook:
        return self.messenger.facebook

    @property
    def database(self) -> Database:
        return self.facebook.database

    @property
    def session(self) -> Session:
        return self.messenger.current_session()

    def __identifier(self, string: str) -> ID:
        return self.facebook.identifier(string)

    def __name(self, identifier: ID) -> str:
        profile = self.facebook.profile(identifier)
        if profile is not None:
            name = profile.name
            if name is not None:
                return name
        return identifier

    #
    #   check
    #
    def __check_blocked(self, envelope: Envelope) -> Optional[Content]:
        sender = self.__identifier(envelope.sender)
        receiver = self.__identifier(envelope.receiver)
        group = self.__identifier(envelope.group)
        # check block-list
        if self.database.is_blocked(sender=sender, receiver=receiver, group=group):
            nickname = self.__name(identifier=receiver)
            if group is None:
                text = 'Message is blocked by %s' % nickname
            else:
                grp_name = self.__name(identifier=group)
                text = 'Message is blocked by %s in group %s' % (nickname, grp_name)
            # response
            res = TextContent.new(text=text)
            res.group = group
            return res

    def __check_login(self, envelope: Envelope) -> Optional[Content]:
        # check session valid
        session = self.session
        if session is None:
            res = TextContent.new(text='Session not found')
            res.group = envelope.group
            return res
        if not session.valid or session.identifier != envelope.sender:
            return HandshakeCommand.ask(session=session.session_key)

    #
    #   filters
    #
    def check_broadcast(self, msg: ReliableMessage) -> Optional[Content]:
        res = self.__check_login(envelope=msg.envelope)
        if res is not None:
            # session invalid
            return res
        res = self.__check_blocked(envelope=msg.envelope)
        if res is not None:
            # blocked
            return res

    def check_deliver(self, msg: ReliableMessage) -> Optional[Content]:
        res = self.__check_login(envelope=msg.envelope)
        if res is not None:
            # session invalid
            return res
        res = self.__check_blocked(envelope=msg.envelope)
        if res is not None:
            # blocked
            return res

    def check_forward(self, msg: ReliableMessage) -> Optional[Content]:
        res = self.__check_login(envelope=msg.envelope)
        if res is not None:
            # session invalid
            return res
        res = self.__check_blocked(envelope=msg.envelope)
        if res is not None:
            # blocked
            return res
