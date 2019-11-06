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
    Messenger
    ~~~~~~~~~

    Transform and send message
"""

from typing import Optional

from dimp import ID, User
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimp import Content, ForwardContent
from dimsdk import Messenger as Transceiver
from dimsdk import ContentProcessor

from .facebook import Facebook


class Messenger(Transceiver):

    def __init__(self):
        super().__init__()
        self.users = []  # list of User
        self.context = {}

    @property
    def current_user(self) -> User:
        return self.users[0]

    #
    #   super()
    #
    def cpu(self) -> ContentProcessor:
        processor = super().cpu()
        for key, value in self.context.items():
            processor.context[key] = value
        return processor

    def send_content(self, content: Content, receiver: ID) -> bool:
        sender = self.current_user.identifier
        msg = InstantMessage.new(content=content, sender=sender, receiver=receiver)
        return self.send_message(msg=msg)

    def deliver_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        # TODO: call dispatcher to deliver this message
        pass

    def forward_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        sender = self.current_user.identifier
        receiver = self.barrack.identifier(msg.envelope.receiver)
        cmd = ForwardContent.new(message=msg)
        msg = InstantMessage.new(content=cmd, sender=sender, receiver=receiver)
        return self.encrypt_sign(msg=msg)

    #
    #   Transform
    #
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        if msg.meta is None:
            facebook: Facebook = self.barrack
            sender = facebook.identifier(msg.envelope.sender)
            meta = facebook.meta(identifier=sender)
            if meta is None:
                # TODO: keep this message in waiting list for meta response
                return None
        return super().verify_message(msg=msg)

    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        receiver = self.barrack.identifier(msg.envelope.receiver)
        if receiver.type.is_group():
            # trim it
            msg = self.__trim(msg=msg, group=receiver)
        else:
            msg = self.__select(msg=msg, receiver=receiver)
        if msg is not None:
            return super().decrypt_message(msg=msg)

    def __select(self, msg: SecureMessage, receiver: ID) -> Optional[SecureMessage]:
        index = 0
        current = None
        for item in self.users:
            if item.identifier == receiver:
                current = item
                break
            else:
                index += 1
        if 0 < index < len(self.users):
            # move this user in front for next message
            current = self.users.pop(index)
            self.users.insert(0, current)
        if current is not None:
            return msg

    def __trim(self, msg: SecureMessage, group: ID) -> Optional[SecureMessage]:
        facebook: Facebook = self.barrack
        members = facebook.members(identifier=group)
        if members is None:
            # TODO: query group members
            return None
        for item in self.users:
            identifier = item.identifier
            if identifier in members:
                # got it
                self.__alter(identifier=identifier)
                return msg.trim(member=identifier)
