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
    Command Processor for 'block'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Block protocol
"""

from typing import List

from dimples import ReliableMessage
from dimples import Content, Command, BaseCommand
from dimples import BaseCommandProcessor

from ...database import Database
from ...common import BlockCommand
from ...common import CommonFacebook


class BlockCommandProcessor(BaseCommandProcessor):

    @property
    def facebook(self) -> CommonFacebook:
        barrack = super().facebook
        assert isinstance(barrack, CommonFacebook), 'facebook error: %s' % barrack
        return barrack

    @property
    def database(self) -> Database:
        db = self.facebook.database
        assert isinstance(db, Database), 'database error: %s' % db
        return db

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, BlockCommand), 'block command error: %s' % content
        sender = msg.sender
        db = self.database
        if 'list' in content:
            # upload block-list, save it
            if db.save_block_command(content=content, identifier=sender):
                return self._respond_text(text='Block received.', extra={
                    'template': 'Block command received: ${ID}.',
                    'replacements': {
                        'ID': str(sender),
                    }
                })
            else:
                return self._respond_text(text='Block not changed.', extra={
                    'template': 'Block command not changed: ${ID}.',
                    'replacements': {
                        'ID': str(sender),
                    }
                })
        else:
            # query block-list, load it
            stored: Command = db.block_command(identifier=sender)
            if stored is not None:
                # response the stored block command directly
                return [stored]
            else:
                # return TextContent.new(text='Sorry, block-list of %s not found.' % sender)
                # TODO: here should response an empty HistoryCommand: 'block'
                res = BaseCommand(cmd=BlockCommand.BLOCK)
                res['list'] = []
                return [res]
