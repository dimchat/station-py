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
    Server extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

from typing import Optional

from dimp import NetworkType
from dimp import InstantMessage, ReliableMessage
from dimp import Envelope, Content
from dimsdk import HandshakeCommand, ReceiptCommand

from ..common import CommonProcessor


class ClientProcessor(CommonProcessor):

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> Optional[Content]:
        res = super().process_content(content=content, r_msg=r_msg)
        if res is None:
            # respond nothing
            return None
        elif isinstance(res, HandshakeCommand):
            # urgent command
            return res
        elif isinstance(res, ReceiptCommand):
            receiver = r_msg.receiver
            if receiver.type == NetworkType.STATION:
                # no need to respond receipt to station
                return None
        # check receiver
        receiver = r_msg.receiver
        user = self.facebook.select_user(receiver=receiver)
        assert user is not None, 'receiver error: %s' % receiver
        # pack message
        env = Envelope.create(sender=user.identifier, receiver=r_msg.sender)
        i_msg = InstantMessage.create(head=env, body=res)
        # normal response
        self.messenger.send_message(msg=i_msg)
        # DON'T respond to station directly
        return None
