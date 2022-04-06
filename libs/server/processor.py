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

from dimp import NetworkType
from dimp import ReliableMessage
from dimp import Content, ContentType, TextContent, Command
from dimsdk import ReceiptCommand, HandshakeCommand
from dimsdk import ContentProcessor, ContentProcessorCreator

from ..database import Database
from ..common import ReportCommand, SearchCommand
from ..common import CommonProcessor, CommonContentProcessorCreator

from .session_server import SessionServer
from .messenger import ServerMessenger


g_database = Database()
g_session_server = SessionServer()


class ServerProcessor(CommonProcessor):

    @property
    def messenger(self) -> ServerMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, ServerMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        # 0. process first
        responses = super().process_content(content=content, r_msg=r_msg)
        messenger = self.messenger
        sender = r_msg.sender
        # 1. check login
        session = messenger.session
        if session is not None:
            if session.identifier is None or not session.active:
                # not login yet, force to handshake again
                if not isinstance(content, HandshakeCommand):
                    handshake = HandshakeCommand.ask(session=session.key)
                    responses.insert(0, handshake)
        # 2. check response
        contents = []
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
            contents.append(res)
        # OK
        return contents

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return ServerContentProcessorCreator(facebook=self.facebook, messenger=self.messenger)


class ServerContentProcessorCreator(CommonContentProcessorCreator):

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd_name: str) -> Optional[ContentProcessor]:
        # document
        if cmd_name == Command.DOCUMENT:
            from .cpu import DocumentCommandProcessor
            return DocumentCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # handshake
        if cmd_name == Command.HANDSHAKE:
            from .cpu import HandshakeCommandProcessor
            return HandshakeCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # login
        if cmd_name == Command.LOGIN:
            from .cpu import LoginCommandProcessor
            return LoginCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # report
        if cmd_name == ReportCommand.REPORT:
            from .cpu import ReportCommandProcessor
            return ReportCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name == 'broadcast':
            from .cpu import ReportCommandProcessor
            return ReportCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name == 'apns':
            from .cpu import APNsCommandProcessor
            return APNsCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name == ReportCommand.ONLINE:
            from .cpu import OnlineCommandProcessor
            return OnlineCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name == ReportCommand.OFFLINE:
            from .cpu import OfflineCommandProcessor
            return OfflineCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # search
        if cmd_name == SearchCommand.SEARCH:
            from .cpu import SearchCommandProcessor
            return SearchCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        elif cmd_name == SearchCommand.ONLINE_USERS:
            from .cpu import SearchCommandProcessor
            return SearchCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd_name=cmd_name)
