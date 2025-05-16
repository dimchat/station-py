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

from dimples import ReliableMessage
from dimples import CommonFacebook, CommonMessenger
from dimples.server import ServerMessagePacker as SuperPacker

from ..utils.mtp import MTPUtils


class ServerPacker(SuperPacker):

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

    # Override
    async def serialize_message(self, msg: ReliableMessage) -> bytes:
        if self.mtp_format == self.MTP_JSON:
            # JsON
            return await super().serialize_message(msg=msg)
        else:
            # D-MTP
            return MTPUtils.serialize_message(msg=msg)

    # Override
    async def deserialize_message(self, data: bytes) -> Optional[ReliableMessage]:
        if data is None or len(data) < 2:
            return None
        if data.startswith(b'{'):
            # JsON
            msg = await super().deserialize_message(data=data)
        else:
            # D-MTP
            msg = MTPUtils.deserialize_message(data=data)
            if msg is not None:
                # FIXME: just change it when first package received
                self.mtp_format = self.MTP_DMTP
        return msg

    # # Override
    # async def encrypt_message(self, msg: InstantMessage) -> Optional[SecureMessage]:
    #     # make sure visa.key exists before encrypting message
    #     # call super to encrypt message
    #     s_msg = await super().encrypt_message(msg=msg)
    #     receiver = msg.receiver
    #     if receiver.is_group:
    #         # reuse group message keys
    #         key = self.messenger.get_cipher_key(sender=msg.sender, receiver=receiver)
    #         key['reused'] = True
    #     # TODO: reuse personal message key?
    #     return s_msg
