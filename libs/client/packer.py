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

from dimples import InstantMessage, SecureMessage, ReliableMessage
from dimples import DocumentCommand, ReceiptCommand

from dimples.common import CommonFacebook
from dimples.client.packer import attach_key_digest
from dimples.client import ClientMessagePacker as SuperPacker
from dimples.client import ClientMessenger

from ..utils.mtp import MTPUtils
from ..common.compatible import fix_meta_attachment
from ..common.compatible import fix_receipt_command
from ..common.compatible import fix_document_command


class ClientPacker(SuperPacker):

    MTP_JSON = 0x01
    MTP_DMTP = 0x02

    def __init__(self, facebook: CommonFacebook, messenger: ClientMessenger):
        super().__init__(facebook=facebook, messenger=messenger)
        # Message Transfer Protocol
        self.mtp_format = self.MTP_JSON

    @property
    def messenger(self) -> ClientMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, ClientMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def serialize_message(self, msg: ReliableMessage) -> bytes:
        fix_meta_attachment(msg=msg)
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
        else:
            # D-MTP
            msg = MTPUtils.deserialize_message(data=data)
            if msg is not None:
                # FIXME: just change it when first package received
                self.mtp_format = self.MTP_DMTP
        if msg is not None:
            fix_meta_attachment(msg=msg)
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
