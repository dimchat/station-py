# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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
    Messenger for request handler in station
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

from typing import Optional, List

from dimples import SymmetricKey
from dimples import Content, TextContent, Command
from dimples import InstantMessage, SecureMessage, ReliableMessage

from dimples.server import ServerMessenger as SuperMessenger
from dimples.server import BlockFilter as SuperBlockFilter
from dimples.server import MuteFilter as SuperMuteFilter
from dimples.server.pusher import get_name

from ..common.compatible import fix_command
from ..database import Database

from .monitor import Monitor


class ServerMessenger(SuperMessenger):

    # Override
    def handshake_success(self):
        # monitor
        session = self.session
        monitor = Monitor()
        monitor.user_online(sender=session.identifier, when=None, remote_address=session.remote_address)
        # process suspended messages
        super().handshake_success()

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        monitor = Monitor()
        monitor.message_received(msg=msg)
        return super().process_reliable_message(msg=msg)

    # Override
    def is_blocked(self, msg: ReliableMessage) -> bool:
        blocked = super().is_blocked(msg=msg)
        if blocked:
            sender = msg.sender
            receiver = msg.receiver
            group = msg.group
            facebook = self.__facebook
            nickname = get_name(identifier=receiver, facebook=facebook)
            if group is None:
                text = 'Message is blocked by %s' % nickname
            else:
                grp_name = get_name(identifier=group, facebook=facebook)
                text = 'Message is blocked by %s in group %s' % (nickname, grp_name)
            # response
            res = TextContent.create(text=text)
            res.group = group
            self.send_content(sender=None, receiver=sender, content=res, priority=1)
            return True

    # Override
    def serialize_content(self, content: Content, key: SymmetricKey, msg: InstantMessage) -> bytes:
        if isinstance(content, Command):
            content = fix_command(content=content)
        return super().serialize_content(content=content, key=key, msg=msg)

    # Override
    def deserialize_content(self, data: bytes, key: SymmetricKey, msg: SecureMessage) -> Optional[Content]:
        content = super().deserialize_content(data=data, key=key, msg=msg)
        if isinstance(content, Command):
            content = fix_command(content=content)
        return content


class BlockFilter(SuperBlockFilter):

    def __init__(self, database: Database):
        super().__init__()
        self.__database = database

    # Override
    def is_blocked(self, msg: ReliableMessage) -> bool:
        blocked = super().is_blocked(msg=msg)
        if blocked:
            return True
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        # check block-list
        db = self.__database
        return db.is_blocked(sender=sender, receiver=receiver, group=group)


class MuteFilter(SuperMuteFilter):

    def __init__(self, database: Database):
        super().__init__()
        self.__database = database

    # Override
    def is_muted(self, msg: ReliableMessage) -> bool:
        muted = super().is_muted(msg=msg)
        if muted:
            return True
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        # check block-list
        db = self.__database
        return db.is_muted(sender=sender, receiver=receiver, group=group)
