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

from dimp import Envelope, ReliableMessage

from libs.common import Log, Messenger
from libs.server import Session

from .config import g_database, g_facebook


class Filter:

    def __init__(self, messenger: Messenger):
        super().__init__()
        # messenger
        self.messenger = messenger

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    @property
    def session(self) -> Session:
        return self.messenger.current_session()

    def is_blocked(self, envelope: Envelope) -> bool:
        sender = g_facebook.identifier(envelope.sender)
        receiver = g_facebook.identifier(envelope.receiver)
        group = g_facebook.identifier(envelope.group)
        # check block-list
        if g_database.is_blocked(sender=sender, receiver=receiver, group=group):
            nickname = g_facebook.nickname(identifier=receiver)
            if group is None:
                self.info('Message is blocked by %s' % nickname)
            else:
                grp_name = g_facebook.group_name(identifier=group)
                self.info('Message is blocked by %s in group %s' % (nickname, grp_name))
            return True

    def is_login(self) -> bool:
        # TODO: check whether deliver this message
        # 1. session valid
        session = self.session
        if session is None:
            self.error('session not found')
            return False
        return session.valid

    #
    #   filters
    #
    def allow_broadcast(self, msg: ReliableMessage) -> bool:
        if not self.is_login():
            return False
        if self.is_blocked(envelope=msg.envelope):
            return False
        return True

    def allow_deliver(self, msg: ReliableMessage) -> bool:
        if not self.is_login():
            return False
        if self.is_blocked(envelope=msg.envelope):
            return False
        return True

    def allow_forward(self, msg: ReliableMessage) -> bool:
        if not self.is_login():
            return False
        if self.is_blocked(envelope=msg.envelope):
            return False
        return True
