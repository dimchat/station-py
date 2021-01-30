# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Server extensions for MessageTransmitter
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional

from dimp import Envelope, InstantMessage, ReliableMessage
from dimsdk import MessageTransmitter

from .dispatcher import Dispatcher
from .facebook import ServerFacebook
from .messenger import ServerMessenger
from .filter import Filter


g_facebook = ServerFacebook()
g_dispatcher = Dispatcher()


class ServerTransmitter(MessageTransmitter):

    def __init__(self, messenger: ServerMessenger):
        super().__init__(messenger=messenger)
        self.__filter = Filter(messenger=messenger)

    @property
    def messenger(self) -> ServerMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, ServerMessenger), 'messenger error: %s' % transceiver
        return transceiver

    @property
    def filter(self) -> Filter:
        return self.__filter

    @property
    def facebook(self) -> ServerFacebook:
        return g_facebook

    @property
    def dispatcher(self) -> Dispatcher:
        return g_dispatcher

    def deliver_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        """ Deliver message to the receiver, or broadcast to neighbours """
        # FIXME: check deliver permission
        res = self.filter.check_deliver(msg=msg)
        if res is None:
            # delivering is allowed, call dispatcher to deliver this message
            res = self.dispatcher.deliver(msg=msg)
        # pack response
        if res is not None:
            user = self.facebook.current_user
            env = Envelope.create(sender=user.identifier, receiver=msg.sender)
            i_msg = InstantMessage.create(head=env, body=res)
            s_msg = self.messenger.encrypt_message(msg=i_msg)
            if s_msg is None:
                raise AssertionError('failed to respond to: %s' % msg.sender)
            return self.messenger.sign_message(msg=s_msg)
