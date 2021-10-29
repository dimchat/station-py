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
    Command Processor for 'storage'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    storage protocol: post/get contacts, private_key, ...
"""

from typing import List

from dimp import ReliableMessage
from dimp import Content, Command
from dimsdk import StorageCommand
from dimsdk import CommandProcessor

from ...database import Database


g_database = Database()


class StorageCommandProcessor(CommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, StorageCommand), 'command error: %s' % cmd
        title = cmd.title
        if title == StorageCommand.CONTACTS:
            if cmd.data is None and 'contacts' not in cmd:
                # query contacts, load it
                stored = g_database.contacts_command(identifier=msg.sender)
                # response
                if stored is None:
                    text = 'Sorry, contacts of %s not found.' % msg.sender
                    return self._respond_text(text=text)
                else:
                    # response the stored contacts command directly
                    return [stored]
            else:
                # upload contacts, save it
                if g_database.save_contacts_command(cmd=cmd, sender=msg.sender):
                    text = 'Contacts of %s received!' % msg.sender
                    return self._respond_receipt(text=text)
                else:
                    text = 'Sorry, contacts not stored %s!' % cmd
                    return self._respond_text(text=text)
        else:
            text = 'Storage command (title: %s) not support yet!' % title
            return self._respond_text(text=text)


# register
spu = StorageCommandProcessor()
CommandProcessor.register(command=StorageCommand.STORAGE, cpu=spu)
CommandProcessor.register(command=StorageCommand.CONTACTS, cpu=spu)
CommandProcessor.register(command=StorageCommand.PRIVATE_KEY, cpu=spu)
