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
    Common extensions for MessagePacker
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from typing import Optional

from dimp import base64_encode, sha256
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimsdk import MessagePacker

from libs.utils.mtp import MTPUtils

from .messenger import CommonMessenger


class CommonPacker(MessagePacker):

    MTP_JSON = 0x01
    MTP_DMTP = 0x02

    def __init__(self, messenger: CommonMessenger):
        super().__init__(messenger=messenger)
        # Message Transfer Protocol
        self.mtp_format = self.MTP_JSON

    def __attach_key_digest(self, msg: ReliableMessage):
        # check message delegate
        if msg.delegate is None:
            msg.delegate = self.transceiver
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
        sender = msg.sender
        group = msg.group
        if group is None:
            receiver = msg.receiver
            key = self.key_cache.cipher_key(sender=sender, receiver=receiver)
        else:
            key = self.key_cache.cipher_key(sender=sender, receiver=group)
        # get key data
        data = key.data
        if data is None or len(data) < 6:
            return
        # get digest
        pos = len(data) - 6
        digest = sha256(data[pos:])
        base64 = base64_encode(digest)
        # set digest
        pos = len(base64) - 8
        keys['digest'] = base64[pos:]
        msg['keys'] = keys

    def serialize_message(self, msg: ReliableMessage) -> bytes:
        self.__attach_key_digest(msg=msg)
        if self.mtp_format == self.MTP_JSON:
            # JsON
            return super().serialize_message(msg=msg)
        else:
            # D-MTP
            return MTPUtils.serialize_message(msg=msg)

    def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        if data is None or len(data) < 2:
            return None
        if data.startswith(b'{'):
            # JsON
            return super().deserialize_message(data=data)
        else:
            # D-MTP
            return MTPUtils.deserialize_message(data=data)

    def encrypt_message(self, msg: InstantMessage) -> SecureMessage:
        s_msg = super().encrypt_message(msg=msg)
        receiver = msg.receiver
        if receiver.is_group:
            # reuse group message keys
            key = self.key_cache.cipher_key(sender=msg.sender, receiver=receiver)
            key['reused'] = True
        # TODO: reuse personal message key?
        return s_msg

    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        key = self.facebook.public_key_for_encryption(identifier=msg.sender)
        if key is None:
            # sender's meta/visa not ready
            self.messenger.suspend_message(msg=msg)
            return None
        return super().verify_message(msg=msg)
