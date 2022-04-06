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
from typing import List, Optional, Union

from startrek import DeparturePriority

from dimp import NetworkType
from dimp import SecureMessage, ReliableMessage
from dimp import ContentType, Content, TextContent, Command
from dimsdk import HandshakeCommand, ReceiptCommand
from dimsdk import ContentProcessor, ContentProcessorCreator

from ..common import CommonProcessor, CommonContentProcessorCreator

from .cpu import ChatTextContentProcessor


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
            # normal response
            messenger.send_content(sender=user.identifier, receiver=r_msg.sender,
                                   content=res, priority=DeparturePriority.NORMAL)
        # DON'T respond to station directly
        return []

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return ClientContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


class ClientContentProcessorCreator(CommonContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # text
        if msg_type == ContentType.TEXT:
            return ChatTextContentProcessor(facebook=self.facebook, messenger=self.messenger, bots=[])
        # others
        return super().create_content_processor(msg_type=msg_type)

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd_name: str) -> Optional[ContentProcessor]:
        # handshake
        if cmd_name == Command.HANDSHAKE:
            from .cpu import HandshakeCommandProcessor
            return HandshakeCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # login
        if cmd_name == Command.LOGIN:
            from .cpu import LoginCommandProcessor
            return LoginCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd_name=cmd_name)
