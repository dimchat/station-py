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

from typing import Optional, Union

from dimsdk import ContentType
from dimsdk import ContentProcessor
from dimsdk import ContentProcessorCreator
from dimsdk import BaseContentProcessor

from dimples.server import ServerProcessor as SuperProcessor
from dimples.server import ServerContentProcessorCreator as SuperCreator

from ..common import ReceiptCommand
from ..common import MuteCommand, BlockCommand
from ..common import StorageCommand
from ..common import ReportCommand, SearchCommand

from .cpu import ReceiptCommandProcessor
from .cpu import MuteCommandProcessor, BlockCommandProcessor
from .cpu import StorageCommandProcessor
from .cpu import ReportCommandProcessor
from .cpu import SearchCommandProcessor


class ServerProcessor(SuperProcessor):

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return ServerContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


class ServerContentProcessorCreator(SuperCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # default
        if msg_type == 0:
            return BaseContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd_name: str) -> Optional[ContentProcessor]:
        # receipt
        if cmd_name == ReceiptCommand.RECEIPT:
            return ReceiptCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # mute
        if cmd_name == MuteCommand.MUTE:
            return MuteCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # block
        if cmd_name == BlockCommand.BLOCK:
            return BlockCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # storage
        if cmd_name == StorageCommand.STORAGE:
            return StorageCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name in [StorageCommand.CONTACTS, StorageCommand.PRIVATE_KEY]:
            return StorageCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # report
        if cmd_name == ReportCommand.REPORT:
            return ReportCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name in ['broadcast', 'apns', ReportCommand.ONLINE, ReportCommand.OFFLINE]:
            return ReportCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # search
        if cmd_name == SearchCommand.SEARCH:
            return SearchCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name == SearchCommand.ONLINE_USERS:
            return SearchCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd_name=cmd_name)
