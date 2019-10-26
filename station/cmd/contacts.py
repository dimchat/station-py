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
    Command Processor for 'contacts'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    storage protocol: post/get contacts
"""

from dimp import ID
from dimp import Content, TextContent
from dimp import Command

from libs.common import ReceiptCommand

from .cpu import CPU


class ContactsCommandProcessor(CPU):

    def process(self, cmd: Command, sender: ID) -> Content:
        if 'data' in cmd or 'contacts' in cmd:
            # receive encrypted contacts, save it
            if self.facebook.save_contacts_command(cmd=cmd, sender=sender):
                self.info('contacts command saved for %s' % sender)
                return ReceiptCommand.receipt(message='Contacts of %s received!' % sender)
            else:
                self.error('failed to save contacts command: %s' % cmd)
                return TextContent.new(text='Contacts not stored %s!' % cmd)
        # query encrypted contacts, load it
        self.info('search contacts(command with encrypted data) for %s' % sender)
        stored: Command = self.facebook.contacts_command(identifier=sender)
        # response
        if stored is not None:
            # response the stored contacts command directly
            return stored
        else:
            return TextContent.new(text='Sorry, contacts of %s not found.' % sender)
