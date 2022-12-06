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

from dimples import ID
from dimples import InstantMessage, SecureMessage, ReliableMessage
from dimples import DocumentCommand

from dimples.common.packer import attach_key_digest
from dimples.common import CommonPacker as SuperPacker
from dimples.common import CommonFacebook, CommonMessenger

from ..utils.mtp import MTPUtils

from .protocol import ReceiptCommand


class CommonPacker(SuperPacker):

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

    def __is_waiting(self, identifier: ID) -> bool:
        if identifier.is_group:
            # checking group meta
            return self.facebook.meta(identifier=identifier) is None
        else:
            # checking visa key
            return self.facebook.public_key_for_encryption(identifier=identifier) is None

    # Override
    def serialize_message(self, msg: ReliableMessage) -> bytes:
        attach_key_digest(msg=msg, messenger=self.messenger)
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
    def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
        # make sure visa.key exists before encrypting message
        content = msg.content
        if isinstance(content, ReceiptCommand):
            # compatible with v1.0
            fix_receipt_command(content=content)
        # call super to encrypt message
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
        i_msg = super().decrypt_message(msg=msg)
        if i_msg is not None:
            content = i_msg.content
            if isinstance(content, ReceiptCommand):
                # compatible with v1.0
                fix_receipt_command(content=content)
            elif isinstance(content, DocumentCommand):
                # compatible with v1.0
                fix_document_command(content=content)
        return i_msg


# TODO: remove after all server/client upgraded
def fix_receipt_command(content: ReceiptCommand):
    origin = content.get('origin')
    if origin is not None:
        # (v2.0)
        # compatible with v1.0
        content['envelope'] = origin
        return content
    # check for old version
    env = content.get('envelope')
    if env is not None:
        # (v1.0)
        # compatible with v2.0
        content['origin'] = env
        return content
    # check for older version
    if 'sender' in content:  # and 'receiver' in content:
        # older version
        env = {
            'sender': content.get('sender'),
            'receiver': content.get('receiver'),
            'time': content.get('time'),
            'sn': content.get('sn'),
            'signature': content.get('signature'),
        }
        content['origin'] = env
        content['envelope'] = env
        return content


# TODO: remove after all server/client upgraded
def fix_document_command(content: DocumentCommand):
    info = content.get('document')
    if info is not None:
        # (v2.0)
        #    "ID"      : "{ID}",
        #    "document" : {
        #        "ID"        : "{ID}",
        #        "data"      : "{JsON}",
        #        "signature" : "{BASE64}"
        #    }
        return content
    info = content.get('profile')
    if info is None:
        # query document command
        return content
    # 1.* => 2.0
    content.pop('profile')
    if isinstance(info, str):
        # compatible with v1.0
        #    "ID"        : "{ID}",
        #    "profile"   : "{JsON}",
        #    "signature" : "{BASE64}"
        content['document'] = {
            'ID': str(content.identifier),
            'data': info,
            'signature': content.get("signature")
        }
    else:
        # compatible with v1.1
        #    "ID"      : "{ID}",
        #    "profile" : {
        #        "ID"        : "{ID}",
        #        "data"      : "{JsON}",
        #        "signature" : "{BASE64}"
        #    }
        content['document'] = info
    return content


# TODO: remove after all server/client upgraded
def fix_visa(msg: ReliableMessage):
    # move 'profile' -> 'visa'
    profile = msg.get('profile')
    if profile is not None:
        msg.pop('profile')
        # 1.* => 2.0
        visa = msg.get('visa')
        if visa is None:
            msg['visa'] = profile
