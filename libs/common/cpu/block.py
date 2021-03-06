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

from typing import Optional

from dimp import ReliableMessage
from dimp import Content, TextContent
from dimp import Command
from dimsdk import ReceiptCommand, BlockCommand
from dimsdk import CommandProcessor

from ..database import Database


g_database = Database()


class BlockCommandProcessor(CommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, BlockCommand), 'block command error: %s' % cmd
        if 'list' in cmd:
            # upload block-list, save it
            if g_database.save_block_command(cmd=cmd, sender=msg.sender):
                return ReceiptCommand(message='Block command of %s received!' % msg.sender)
            else:
                return TextContent(text='Sorry, block-list not stored: %s!' % cmd)
        else:
            # query block-list, load it
            stored: Command = g_database.block_command(identifier=msg.sender)
            if stored is not None:
                # response the stored block command directly
                return stored
            else:
                # return TextContent.new(text='Sorry, block-list of %s not found.' % sender)
                # TODO: here should response an empty HistoryCommand: 'block'
                res = Command(command=BlockCommand.BLOCK)
                res['list'] = []
                return res


# register
CommandProcessor.register(command=BlockCommand.BLOCK, cpu=BlockCommandProcessor())
