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

import time
from typing import List

from dimp import NetworkType
from dimp import InstantMessage, SecureMessage, ReliableMessage
from dimp import Envelope, Content, TextContent
from dimsdk import HandshakeCommand, ReceiptCommand

from ..common import CommonProcessor


class ClientProcessor(CommonProcessor):

    # Override
    def process_secure_message(self, msg: SecureMessage, r_msg: ReliableMessage) -> List[SecureMessage]:
        try:
            return super().process_secure_message(msg=msg, r_msg=r_msg)
        except LookupError as error:
            if str(error).startswith('receiver error'):
                # not mine? ignore it
                return []
            else:
                raise error

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        responses = super().process_content(content=content, r_msg=r_msg)
        if responses is None or len(responses) == 0:
            # respond nothing
            return []
        elif isinstance(responses[0], HandshakeCommand):
            # urgent command
            return responses
        sender = r_msg.sender
        receiver = r_msg.receiver
        user = self.facebook.select_user(receiver=receiver)
        assert user is not None, 'receiver error: %s' % receiver
        messenger = self.messenger
        # check responses
        for res in responses:
            if res is None:
                # should not happen
                continue
            elif isinstance(res, ReceiptCommand):
                if sender.type == NetworkType.STATION:
                    # no need to respond receipt to station
                    when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r_msg.time))
                    self.info('drop receipt responding to %s, origin msg time=[%s]' % (sender, when))
                    continue
            elif isinstance(res, TextContent):
                if sender.type == NetworkType.STATION:
                    # no need to respond text message to station
                    when = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r_msg.time))
                    self.info('drop text msg responding to %s, origin time=[%s], text=%s' % (sender, when, res.text))
                    continue
            # pack message
            env = Envelope.create(sender=user.identifier, receiver=r_msg.sender)
            i_msg = InstantMessage.create(head=env, body=res)
            # normal response
            messenger.send_instant_message(msg=i_msg)
        # DON'T respond to station directly
        return []
