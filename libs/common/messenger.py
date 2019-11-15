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

from abc import ABC
from typing import Optional

from dimp import ID, User
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import Messenger


class CommonMessenger(Messenger, ABC):

    #
    #   switch current user
    #
    def __select(self, receiver: ID=None, group: ID=None) -> Optional[User]:
        """ Select a local user for decrypting message """
        local_users = self.local_users
        if receiver is None:
            # group message (recipient not designated)
            assert group.type.is_group(), 'group ID error: %s' % group
            if group.is_broadcast:
                return self.current_user
            members = self.facebook.members(identifier=group)
            if members is None:
                # TODO: query group members
                return None
            # check which local user is in the group's member-list
            for user in local_users:
                if user.identifier in members:
                    # got it
                    self.current_user = user
                    return user
            # FIXME: not for you?
        else:
            # 1. personal message
            # 2. split group message
            assert receiver.type.is_user(), 'receiver ID error: %s' % receiver
            if receiver.is_broadcast:
                return self.current_user
            for user in local_users:
                if user.identifier == receiver:
                    # got it
                    self.current_user = user
                    return user

    #
    #   Transform
    #
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        try:
            return super().verify_message(msg=msg)
        except LookupError:
            # TODO: keep this message in waiting list for meta response
            #       (facebook/database should query meta automatically)
            return None

    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        receiver = self.barrack.identifier(msg.envelope.receiver)
        if receiver.type.is_user():
            # check whether the receiver is in local users
            user = self.__select(receiver=receiver)
            if user is None:
                return None
        elif receiver.type.is_group():
            # check which local user is in the group's member-list
            user = self.__select(group=receiver)
            if user is None:
                return None
            # trim it
            msg = msg.trim(member=user.identifier)
        return super().decrypt_message(msg=msg)
