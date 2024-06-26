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

from typing import List

from dimples import DateTime
from dimples import ReliableMessage

from dimples.server import ServerMessenger as SuperMessenger
from dimples.server import BlockFilter as SuperBlockFilter
from dimples.server import MuteFilter as SuperMuteFilter

from ..database import Database

from .monitor import Monitor


class ServerMessenger(SuperMessenger):

    # Override
    async def handshake_success(self):
        # monitor
        session = self.session
        monitor = Monitor()
        monitor.user_online(sender=session.identifier, remote_address=session.remote_address, when=DateTime.now())
        # process suspended messages
        await super().handshake_success()

    # Override
    async def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        monitor = Monitor()
        monitor.message_received(msg=msg)
        return await super().process_reliable_message(msg=msg)


class BlockFilter(SuperBlockFilter):

    def __init__(self, database: Database):
        super().__init__()
        self.__database = database

    # Override
    async def is_blocked(self, msg: ReliableMessage) -> bool:
        blocked = await super().is_blocked(msg=msg)
        if blocked:
            return True
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        # check block-list
        db = self.__database
        return await db.is_blocked(sender=sender, receiver=receiver, group=group)


class MuteFilter(SuperMuteFilter):

    def __init__(self, database: Database):
        super().__init__()
        self.__database = database

    # Override
    async def is_muted(self, msg: ReliableMessage) -> bool:
        muted = await super().is_muted(msg=msg)
        if muted:
            return True
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        # check block-list
        db = self.__database
        return await db.is_muted(sender=sender, receiver=receiver, group=group)
