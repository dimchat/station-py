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

from dimsdk import ReliableMessage
from dimsdk import Content, Command, BaseCommand
from dimsdk import BaseCommandProcessor

from ...database import Database
from ..protocol import BlockCommand


g_database = Database()


class BlockCommandProcessor(BaseCommandProcessor):

    # Override
    def process(self, content: Content, msg: ReliableMessage) -> List[Content]:
        assert isinstance(content, BlockCommand), 'block command error: %s' % content
        if 'list' in content:
            # upload block-list, save it
            if g_database.save_block_command(content=content, sender=msg.sender):
                text = 'Block command of %s received!' % msg.sender
                return self._respond_text(text=text)
            else:
                text = 'Sorry, block-list not stored: %s!' % content
                return self._respond_text(text=text)
        else:
            # query block-list, load it
            stored: Command = g_database.block_command(identifier=msg.sender)
            if stored is not None:
                # response the stored block command directly
                return [stored]
            else:
                # return TextContent.new(text='Sorry, block-list of %s not found.' % sender)
                # TODO: here should response an empty HistoryCommand: 'block'
                res = BaseCommand(cmd=BlockCommand.BLOCK)
                res['list'] = []
                return [res]
