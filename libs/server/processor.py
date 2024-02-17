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

from dimples import ID
from dimples import ContentType
from dimples import ReportCommand, ReceiptCommand
from dimples import ReliableMessage

from dimples import ContentProcessor
from dimples import ContentProcessorCreator
from dimples import BaseContentProcessor

from dimples.server import ServerMessageProcessor
from dimples.server import ServerContentProcessorCreator
from dimples.server import Dispatcher

from ..common import MuteCommand, BlockCommand

from .cpu import AnsCommandProcessor
from .cpu import ReportCommandProcessor
from .cpu import MuteCommandProcessor, BlockCommandProcessor


class ServerProcessor(ServerMessageProcessor):

    # Override
    def is_blocked(self, msg: ReliableMessage) -> bool:
        blocked = super().is_blocked(msg=msg)
        if blocked:
            sender = msg.sender
            receiver = msg.receiver
            group = msg.group
            facebook = self.facebook
            nickname = facebook.get_name(identifier=receiver)
            if group is None:
                text = 'Message is blocked by %s' % nickname
            else:
                grp_name = facebook.get_name(identifier=group)
                text = 'Message is blocked by %s in group %s' % (nickname, grp_name)
            # response
            res = ReceiptCommand.create(text=text, envelope=msg.envelope)
            res.group = group
            self.messenger.send_content(sender=None, receiver=sender, content=res, priority=1)
            return True

    # Override
    def _broadcast_message(self, msg: ReliableMessage, station: ID):
        sender = msg.sender
        receiver = msg.receiver
        assert receiver.is_broadcast, 'broadcast message error: %s -> %s' % (sender, receiver)
        if receiver.is_user:
            # broadcast message (to station bots)
            # e.g.: 'archivist@anywhere', 'announcer@anywhere', 'monitor@anywhere'
            name = receiver.name
            assert name is not None and name != 'station' and name != 'anyone', 'receiver error: %s' % receiver
            bot = AnsCommandProcessor.ans_id(name=name)
            if bot is None:
                self.warning(msg='failed to get receiver: %s' % receiver)
            elif bot == sender:
                self.debug(msg='skip cycled message: %s -> %s' % (sender, receiver))
            elif bot == station:
                self.debug(msg='skip current station: %s -> %s' % (sender, receiver))
            else:
                self.info(msg='forward to bot: %s -> %s' % (name, bot))
                dispatcher = Dispatcher()
                dispatcher.deliver_message(msg=msg, receiver=bot)
                return True
            # ignore this receiver
            return False
        # broadcast group message to neighbor stations
        return super()._broadcast_message(msg=msg, station=station)

    # Override
    def _create_creator(self) -> ContentProcessorCreator:
        return ServerProcessorCreator(facebook=self.facebook, messenger=self.messenger)


class ServerProcessorCreator(ServerContentProcessorCreator):

    # Override
    def create_content_processor(self, msg_type: Union[int, ContentType]) -> Optional[ContentProcessor]:
        # default
        if msg_type == 0:
            return BaseContentProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_content_processor(msg_type=msg_type)

    # Override
    def create_command_processor(self, msg_type: Union[int, ContentType], cmd: str) -> Optional[ContentProcessor]:
        # mute
        if cmd == MuteCommand.MUTE:
            return MuteCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # block
        if cmd == BlockCommand.BLOCK:
            return BlockCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # report
        if cmd in ['broadcast', ReportCommand.ONLINE, ReportCommand.OFFLINE]:
            return ReportCommandProcessor(facebook=self.facebook, messenger=self.messenger)
        # others
        return super().create_command_processor(msg_type=msg_type, cmd=cmd)
