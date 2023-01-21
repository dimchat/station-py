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

from typing import Optional

from dimples import SymmetricKey
from dimples import Envelope, Content, TextContent
from dimples import InstantMessage, SecureMessage, ReliableMessage
from dimples import Command, MetaCommand, ReceiptCommand

from dimples.server import ServerMessenger as SuperMessenger
from dimples.server.pusher import get_name

from ..common.compatible import fix_meta_version, fix_receipt_command
from ..common import CommonFacebook
from ..database import Database


class ServerMessenger(SuperMessenger):

    @property
    def facebook(self) -> CommonFacebook:
        return super().facebook

    @property
    def database(self) -> Database:
        db = super().database
        assert isinstance(db, Database), 'database error: %s' % db
        return db

    # Override
    def verify_message(self, msg: ReliableMessage) -> Optional[SecureMessage]:
        res = self.__check_block(envelope=msg.envelope)
        if res is None:
            return super().verify_message(msg=msg)
        else:
            self.send_content(sender=None, receiver=msg.sender, content=res)

    def __check_block(self, envelope: Envelope) -> Optional[Content]:
        sender = envelope.sender
        receiver = envelope.receiver
        group = envelope.group
        # check block-list
        db = self.database
        if db.is_blocked(sender=sender, receiver=receiver, group=group):
            facebook = self.facebook
            nickname = get_name(identifier=receiver, facebook=facebook)
            if group is None:
                text = 'Message is blocked by %s' % nickname
            else:
                grp_name = get_name(identifier=group, facebook=facebook)
                text = 'Message is blocked by %s in group %s' % (nickname, grp_name)
            # response
            res = TextContent.create(text=text)
            res.group = group
            return res

    # Override
    def serialize_content(self, content: Content, key: SymmetricKey, msg: InstantMessage) -> bytes:
        if isinstance(content, Command):
            content = fix_cmd(content=content)
        return super().serialize_content(content=content, key=key, msg=msg)

    # Override
    def deserialize_content(self, data: bytes, key: SymmetricKey, msg: SecureMessage) -> Optional[Content]:
        content = super().deserialize_content(data=data, key=key, msg=msg)
        if isinstance(content, Command):
            content = fix_cmd(content=content)
        return content


def fix_cmd(content: Command) -> Command:
    # check 'cmd'
    cmd = content.get('cmd')
    if cmd is None:
        # copy 'command' to 'cmd' and recreate it
        cmd = content.get('command')
        content['cmd'] = cmd
        content = Command.parse(content=content)
    elif 'command' not in content:
        content['command'] = cmd
    # check other command
    if isinstance(content, ReceiptCommand):
        fix_receipt_command(content=content)
    elif isinstance(content, MetaCommand):
        meta = content.get('meta')
        if meta is not None:
            fix_meta_version(meta=meta)
    return content
