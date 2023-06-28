# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
#
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

from dimples import ID, Envelope, Content, InstantMessage, ReliableMessage
from dimples import CommonFacebook, CommonMessenger
from dimples.server import Dispatcher

from ..utils import Logging


class Emitter(Logging):

    def __init__(self, messenger: CommonMessenger):
        super().__init__()
        self.__messenger = messenger
        self.__dispatcher = None

    @property
    def messenger(self) -> CommonMessenger:
        return self.__messenger

    @property
    def facebook(self) -> CommonFacebook:
        return self.__messenger.facebook

    @property
    def dispatcher(self) -> Dispatcher:
        if self.__dispatcher is None:
            self.__dispatcher = Dispatcher()
        return self.__dispatcher

    def send_content(self, content: Content, receiver: ID) -> bool:
        facebook = self.facebook
        current = facebook.current_user
        sender = current.identifier
        assert sender is not None, 'current user error: %s' % current
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        return self.send_instant_message(msg=i_msg)

    def send_instant_message(self, msg: InstantMessage) -> bool:
        messenger = self.messenger
        s_msg = messenger.encrypt_message(msg=msg)
        if s_msg is None:
            self.error(msg='failed to encrypt message: %s -> %s' % (msg.sender, msg.receiver))
            return False
        r_msg = messenger.sign_message(msg=s_msg)
        if r_msg is None:
            self.error(msg='failed to sign message: %s -> %s' % (msg.sender, msg.receiver))
            return False
        self.info(msg='sending message: %s -> %s' % (msg.sender, msg.receiver))
        self.send_reliable_message(msg=r_msg)
        return True

    def send_reliable_message(self, msg: ReliableMessage):
        dispatcher = self.dispatcher
        dispatcher.deliver_message(msg=msg, receiver=msg.receiver)
