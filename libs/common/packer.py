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

from startrek import DeparturePriority

from dimp import base64_encode, sha256
from dimp import ID, Meta
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimp import DocumentCommand
from dimsdk import MessagePacker

from ..utils.mtp import MTPUtils

from .facebook import CommonFacebook
from .messenger import CommonMessenger


class CommonPacker(MessagePacker):

    MTP_JSON = 0x01
    MTP_DMTP = 0x02

    def __init__(self, facebook: CommonFacebook, messenger: CommonMessenger):
        super().__init__(facebook=facebook, messenger=messenger)
        # Message Transfer Protocol
        self.mtp_format = self.MTP_JSON

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    def __attach_key_digest(self, msg: ReliableMessage):
        messenger = self.messenger
        # check message delegate
        if msg.delegate is None:
            msg.delegate = messenger
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
            key = messenger.cipher_key(sender=sender, receiver=receiver)
        else:
            key = messenger.cipher_key(sender=sender, receiver=group)
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

    # Override
    def serialize_message(self, msg: ReliableMessage) -> bytes:
        self.__attach_key_digest(msg=msg)
        if self.mtp_format == self.MTP_JSON:
            # JsON
            return super().serialize_message(msg=msg)
        else:
            # D-MTP
            return MTPUtils.serialize_message(msg=msg)

    # Override
    def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        if data is None or len(data) < 2:
            return None
        if data.startswith(b'{'):
            # JsON
            msg = super().deserialize_message(data=data)
            if msg is not None:
                fix_visa(msg=msg)
            return msg
        else:
            # D-MTP
            msg = MTPUtils.deserialize_message(data=data)
            if msg is not None:
                # FIXME: just change it when first package received
                self.mtp_format = self.MTP_DMTP
                return msg

    # Override
    def sign_message(self, msg: SecureMessage) -> ReliableMessage:
        if isinstance(msg, ReliableMessage):
            # already signed
            return msg
        else:
            return super().sign_message(msg=msg)

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        sender = msg.sender
        # [Meta Protocol]
        meta = msg.meta
        if meta is None:
            meta = self.facebook.meta(identifier=sender)
        elif not Meta.matches(meta=meta, identifier=sender):
            meta = None
        if meta is None:
            # NOTICE: the application will query meta automatically,
            #         save this message in a queue waiting sender's meta response
            self.messenger.suspend_message(msg=msg)
            return None
        # make sure meta exists before verifying message
        return super().verify_message(msg=msg)

    def __is_waiting(self, identifier: ID) -> bool:
        if identifier.is_group:
            # checking group meta
            return self.facebook.meta(identifier=identifier) is None
        else:
            # checking visa key
            return self.facebook.public_key_for_encryption(identifier=identifier) is None

    # Override
    def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        receiver = msg.receiver
        group = msg.group
        if not (receiver.is_broadcast or (group is not None and group.is_broadcast)):
            # this message is not a broadcast message
            if self.__is_waiting(receiver) or (group is not None and self.__is_waiting(group)):
                # NOTICE: the application will query visa automatically,
                #         save this message in a queue waiting sender's visa response
                self.messenger.suspend_message(msg=msg)
                return None
        # make sure visa.key exists before encrypting message
        s_msg = super().encrypt_message(msg=msg)
        receiver = msg.receiver
        if receiver.is_group:
            # reuse group message keys
            key = self.messenger.cipher_key(sender=msg.sender, receiver=receiver)
            key['reused'] = True
        # TODO: reuse personal message key?
        return s_msg

    # Override
    def decrypt_message(self, msg: SecureMessage) -> Optional[InstantMessage]:
        try:
            i_msg = super().decrypt_message(msg=msg)
            if i_msg is not None:
                content = i_msg.content
                if isinstance(content, DocumentCommand):
                    fix_profile(cmd=content)
            return i_msg
        except AssertionError as error:
            err_msg = '%s' % error
            # check exception thrown by DKD: chat.dim.dkd.EncryptedMessage.decrypt()
            if err_msg.find('failed to decrypt key in msg') >= 0:
                # visa.key not updated?
                user = self.facebook.current_user
                visa = user.visa
                assert visa is not None and visa.valid, 'user visa error: %s' % user
                cmd = DocumentCommand.response(document=visa, identifier=user.identifier)
                self.messenger.send_content(sender=user.identifier, receiver=msg.sender,
                                            content=cmd, priority=DeparturePriority.NORMAL)
            else:
                raise error


def fix_profile(cmd: DocumentCommand):
    info = cmd.get('document')
    if info is not None:
        # (v2.0)
        #    "ID"      : "{ID}",
        #    "document" : {
        #        "ID"        : "{ID}",
        #        "data"      : "{JsON}",
        #        "signature" : "{BASE64}"
        #    }
        return cmd
    info = cmd.get('profile')
    if info is None:
        # query document command
        return cmd
    # 1.* => 2.0
    cmd.pop('profile')
    if isinstance(info, str):
        # compatible with v1.0
        #    "ID"        : "{ID}",
        #    "profile"   : "{JsON}",
        #    "signature" : "{BASE64}"
        cmd['document'] = {
            'ID': str(cmd.identifier),
            'data': info,
            'signature': cmd.get("signature")
        }
    else:
        # compatible with v1.1
        #    "ID"      : "{ID}",
        #    "profile" : {
        #        "ID"        : "{ID}",
        #        "data"      : "{JsON}",
        #        "signature" : "{BASE64}"
        #    }
        cmd['document'] = info
    return cmd


def fix_visa(msg: ReliableMessage):
    # move 'profile' -> 'visa'
    profile = msg.get('profile')
    if profile is not None:
        msg.pop('profile')
        # 1.* => 2.0
        visa = msg.get('visa')
        if visa is None:
            msg['visa'] = profile
