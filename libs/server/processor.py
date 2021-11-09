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
from typing import List, Optional

from dimp import NetworkType
from dimp import ReliableMessage
from dimp import Content, TextContent, Command
from dimsdk import ReceiptCommand, HandshakeCommand
from dimsdk import CommandProcessor, ProcessorFactory

from ..utils import get_msg_sig
from ..database import Database
from ..common import msg_traced, is_broadcast_message
from ..common import ReportCommand, SearchCommand
from ..common import CommonProcessor, CommonProcessorFactory

from .session import SessionServer
from .messenger import ServerMessenger
from .dispatcher import Dispatcher


g_database = Database()
g_session_server = SessionServer()
g_dispatcher = Dispatcher()


class ServerProcessor(CommonProcessor):

    @property
    def messenger(self) -> ServerMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, ServerMessenger), 'messenger error: %s' % transceiver
        return transceiver

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        messenger = self.messenger
        sender = msg.sender
        receiver = msg.receiver
        #
        # 1. verify message
        #
        s_msg = messenger.verify_message(msg=msg)
        if s_msg is None:
            self.error('failed to verify message: %s -> %s' % (sender, receiver))
            # waiting for sender's meta if not exists
            return []
        # 1.1. check traces
        station = g_dispatcher.station
        if msg_traced(msg=msg, node=station, append=True):
            sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
            self.info('cycled msg [%s]: %s in %s' % (sig, station, msg.get('traces')))
            if sender.type == NetworkType.STATION or receiver.type == NetworkType.STATION:
                self.warning('ignore station msg [%s]: %s -> %s' % (sig, sender, receiver))
                return []
            if is_broadcast_message(msg=msg):
                self.warning('ignore traced broadcast msg [%s]: %s -> %s' % (sig, sender, receiver))
                return []
            sessions = g_session_server.active_sessions(identifier=receiver)
            if len(sessions) > 0:
                self.info('deliver cycled msg [%s]: %s -> %s' % (sig, sender, receiver))
                return messenger.deliver_message(msg=msg)
            else:
                self.info('store cycled msg [%s]: %s -> %s' % (sig, sender, receiver))
                g_database.save_message(msg=msg)
                return []
        # 1.2. check broadcast/group message
        deliver_responses = []
        if receiver.is_broadcast:
            deliver_responses = messenger.deliver_message(msg=msg)
            # if this is a broadcast, deliver it, send back the response
            # and continue to process it with the station.
            # because this station is also a recipient too.
        elif receiver.is_group:
            # or, if this is is an ordinary group message,
            # just deliver it to the group assistant
            # and return the response to the sender.
            return messenger.deliver_message(msg=msg)
        elif receiver.type != NetworkType.STATION:
            # receiver not station, deliver it
            return messenger.deliver_message(msg=msg)
        #
        # 2. process message
        #
        try:
            responses = messenger.process_secure_message(msg=s_msg, r_msg=msg)
        except LookupError as error:
            if str(error).startswith('receiver error'):
                # not mine? deliver it
                return messenger.deliver_message(msg=msg)
            else:
                raise error
        #
        # 3. sign messages
        #
        messages = []
        for res in responses:
            r_msg = messenger.sign_message(msg=res)
            if r_msg is None:
                # should not happen
                continue
            group = msg.group
            if receiver == 'station@anywhere' or (group is not None and group.is_broadcast):
                # if this message sent to 'station@anywhere', or with group ID 'stations@everywhere',
                # it means the client doesn't have the station's meta or visa (e.g.: first handshaking),
                # so respond them as message attachments.
                user = self.facebook.user(identifier=r_msg.sender)
                r_msg.meta = user.meta
                r_msg.visa = user.visa
            messages.append(r_msg)
        # append deliver responses
        for r_msg in deliver_responses:
            messages.append(r_msg)
        return messages

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        # 0. process first
        responses = super().process_content(content=content, r_msg=r_msg)
        messenger = self.messenger
        sender = r_msg.sender
        # 1. check login
        session = messenger.current_session
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
    def _create_processor_factory(self) -> ProcessorFactory:
        return ServerProcessorFactory(messenger=self.messenger)


class ServerProcessorFactory(CommonProcessorFactory):

    # Override
    def _create_command_processor(self, msg_type: int, cmd_name: str) -> Optional[CommandProcessor]:
        # document
        if cmd_name == Command.DOCUMENT:
            from .cpu import DocumentCommandProcessor
            return DocumentCommandProcessor(messenger=self.messenger)
        elif cmd_name in ['profile', 'visa', 'bulletin']:
            # share the same processor
            cpu = self._get_command_processor(cmd_name=Command.DOCUMENT)
            if cpu is None:
                from .cpu import DocumentCommandProcessor
                cpu = DocumentCommandProcessor(messenger=self.messenger)
                self._put_command_processor(cmd_name=Command.DOCUMENT, cpu=cpu)
            return cpu
        # handshake
        if cmd_name == Command.HANDSHAKE:
            from .cpu import HandshakeCommandProcessor
            return HandshakeCommandProcessor(messenger=self.messenger)
        # login
        if cmd_name == Command.LOGIN:
            from .cpu import LoginCommandProcessor
            return LoginCommandProcessor(messenger=self.messenger)
        # report
        if cmd_name == ReportCommand.REPORT:
            from .cpu import ReportCommandProcessor
            return ReportCommandProcessor(messenger=self.messenger)
        elif cmd_name == 'broadcast':
            # share the same processor
            cpu = self._get_command_processor(cmd_name=ReportCommand.REPORT)
            if cpu is None:
                from .cpu import ReportCommandProcessor
                cpu = ReportCommandProcessor(messenger=self.messenger)
                self._put_command_processor(cmd_name=ReportCommand.REPORT, cpu=cpu)
            return cpu
        elif cmd_name == 'apns':
            from .cpu import APNsCommandProcessor
            return APNsCommandProcessor(messenger=self.messenger)
        elif cmd_name == ReportCommand.ONLINE:
            from .cpu import OnlineCommandProcessor
            return OnlineCommandProcessor(messenger=self.messenger)
        elif cmd_name == ReportCommand.OFFLINE:
            from .cpu import OfflineCommandProcessor
            return OfflineCommandProcessor(messenger=self.messenger)
        # search
        if cmd_name == SearchCommand.SEARCH:
            from .cpu import SearchCommandProcessor
            return SearchCommandProcessor(messenger=self.messenger)
        elif cmd_name == SearchCommand.ONLINE_USERS:
            # share the same processor
            cpu = self._get_command_processor(cmd_name=SearchCommand.SEARCH)
            if cpu is None:
                from .cpu import SearchCommandProcessor
                cpu = SearchCommandProcessor(messenger=self.messenger)
                self._put_command_processor(cmd_name=SearchCommand.SEARCH, cpu=cpu)
            return cpu
        # others
        return super()._create_command_processor(msg_type=msg_type, cmd_name=cmd_name)
