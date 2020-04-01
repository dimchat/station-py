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
    Common extensions for Messenger
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from typing import Optional, Union

from mkm.crypto.utils import sha256, base64_encode

from dimp import ID
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimp import Content, InviteCommand, ResetCommand

from dimsdk import Messenger


class CommonMessenger(Messenger):

    def __is_empty(self, group: ID) -> bool:
        """
        Check whether group info empty (lost)

        :param group: group ID
        :return: True on members, owner not found
        """
        facebook = self.facebook
        members = facebook.members(identifier=group)
        if members is None or len(members) == 0:
            return True
        owner = facebook.owner(identifier=group)
        if owner is None:
            return True

    def __check_group(self, content: Content, sender: ID) -> bool:
        """
        Check if it is a group message, and whether the group members info needs update

        :param content: message content
        :param sender:  message sender
        :return: True on updating
        """
        facebook = self.facebook
        group = facebook.identifier(content.group)
        if group is None or group.is_broadcast:
            # 1. personal message
            # 2. broadcast message
            return False
        # check meta for new group ID
        meta = facebook.meta(identifier=group)
        if meta is None:
            # NOTICE: if meta for group not found,
            #         facebook should query it from DIM network automatically
            # TODO: insert the message to a temporary queue to wait meta
            # raise LookupError('group meta not found: %s' % group)
            return True
        # query group info
        if self.__is_empty(group=group):
            # NOTICE: if the group info not found, and this is not an 'invite' command
            #         query group info from the sender
            if isinstance(content, InviteCommand) or isinstance(content, ResetCommand):
                # FIXME: can we trust this stranger?
                #        may be we should keep this members list temporary,
                #        and send 'query' to the owner immediately.
                # TODO: check whether the members list is a full list,
                #       it should contain the group owner(owner)
                return False
            else:
                return self.query_group(group=group, users=[sender])
        elif facebook.exists_member(member=sender, group=group):
            # normal membership
            return False
        elif facebook.exists_assistant(member=sender, group=group):
            # normal membership
            return False
        elif facebook.is_owner(member=sender, group=group):
            # normal membership
            return False
        else:
            # if assistants exists, query them
            admins = facebook.assistants(identifier=group)
            # if owner found, query it too
            owner = facebook.owner(identifier=group)
            if owner is not None:
                if admins is None:
                    admins = [owner]
                elif owner not in admins:
                    admins.append(owner)
            return self.query_group(group=group, users=admins)

    def query_meta(self, identifier: ID) -> bool:
        pass

    def query_profile(self, identifier: ID) -> bool:
        pass

    def query_group(self, group: ID, users: list) -> bool:
        pass

    #
    #  Serialization
    #
    def serialize_message(self, msg: ReliableMessage) -> bytes:
        self.__attach_key_digest(msg=msg)
        return super().serialize_message(msg=msg)

    def __attach_key_digest(self, msg: ReliableMessage):
        if msg.delegate is None:
            msg.delegate = self
        if msg.encrypted_key is not None:
            # 'key' exists
            return
        keys = msg.encrypted_keys
        if keys is None:
            keys = {}
        elif 'digest' in keys:
            # key digest already exists
            return
        # get key with direction
        sender = self.barrack.identifier(msg.envelope.sender)
        group = self.barrack.identifier(msg.envelope.group)
        if group is None:
            receiver = self.barrack.identifier(msg.envelope.receiver)
            key = self.key_cache.cipher_key(sender=sender, receiver=receiver)
        else:
            key = self.key_cache.cipher_key(sender=sender, receiver=group)
        # get key data
        data = key.data
        if data is None or len(data) < 8:
            return
        # get digest
        pos = len(data) - 4
        digest = sha256(data[pos:])
        base64 = base64_encode(digest)
        # set digest
        pos = len(base64) - 8
        keys['digest'] = base64[pos:]
        msg['keys'] = keys

    def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        if data is None or len(data) == 0:
            return None
        return super().deserialize_message(data=data)

    #
    #   Reuse message key
    #

    def encrypt_message(self, msg: InstantMessage) -> SecureMessage:
        s_msg = super().encrypt_message(msg=msg)
        facebook = self.facebook
        env = msg.envelope
        receiver = facebook.identifier(env.receiver)
        if receiver.is_group:
            # reuse group message keys
            sender = facebook.identifier(env.sender)
            key = self.key_cache.cipher_key(sender=sender, receiver=receiver)
            key['reused'] = True
        # TODO: reuse personal message key?
        return s_msg

    def serialize_key(self, key: dict, msg: InstantMessage) -> Optional[bytes]:
        if key.get('reused'):
            # no need to encrypt reused key again
            return None
        return super().serialize_key(key=key, msg=msg)

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

    # Override
    def process_instant(self, msg: InstantMessage) -> Optional[InstantMessage]:
        sender = self.facebook.identifier(string=msg.envelope.sender)
        if self.__check_group(content=msg.content, sender=sender):
            # save this message in a queue to wait group meta response
            self.suspend_message(msg=msg)
            return None
        return super().process_instant(msg=msg)
