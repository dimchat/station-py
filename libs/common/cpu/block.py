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

from dimp import ID
from dimp import InstantMessage
from dimp import Content, TextContent
from dimp import Command
from dimsdk import ReceiptCommand, BlockCommand
from dimsdk import CommandProcessor

from ..database import Database


class BlockCommandProcessor(CommandProcessor):

    @property
    def database(self) -> Database:
        return self.get_context('database')

    def __get(self, sender: ID) -> Content:
        stored: Command = self.database.block_command(identifier=sender)
        if stored is not None:
            # response the stored block command directly
            return stored
        else:
            # return TextContent.new(text='Sorry, block-list of %s not found.' % sender)
            # TODO: here should response an empty HistoryCommand: 'block'
            res = Command.new(command='block')
            res['list'] = []
            return res

    def __put(self, cmd: BlockCommand, sender: ID) -> Content:
        # receive block command, save it
        if self.database.save_block_command(cmd=cmd, sender=sender):
            return ReceiptCommand.new(message='Block command of %s received!' % sender)
        else:
            return TextContent.new(text='Sorry, block-list not stored: %s!' % cmd)

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Content:
        assert isinstance(content, BlockCommand), 'block command error: %s' % content
        if 'list' in content:
            # upload block-list, save it
            return self.__put(cmd=content, sender=sender)
        else:
            # query block-list, load it
            return self.__get(sender=sender)


# register
CommandProcessor.register(command='block', processor_class=BlockCommandProcessor)
