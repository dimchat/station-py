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

from dimples import ReliableMessage
from dimples import Content
from dimples import BaseCommandProcessor

from ...common import CommonFacebook
from ...database import Database
from ..protocol import StorageCommand


class StorageCommandProcessor(BaseCommandProcessor):

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
        assert isinstance(content, StorageCommand), 'command error: %s' % content
        sender = msg.sender
        title = content.title
        if title == StorageCommand.CONTACTS:
            db = self.database
            if content.data is None and 'contacts' not in content:
                # query contacts, load it
                stored = db.contacts_command(identifier=sender)
                # response
                if stored is None:
                    return self._respond_text(text='Contacts not found.', extra={
                        'template': 'Contacts not found: ${ID}.',
                        'replacements': {
                            'ID': str(sender),
                        }
                    })
                else:
                    # response the stored contacts command directly
                    return [stored]
            else:
                # upload contacts, save it
                if db.save_contacts_command(content=content, identifier=sender):
                    return self._respond_text(text='Contacts received.', extra={
                        'template': 'Contacts received: ${ID}.',
                        'replacements': {
                            'ID': str(sender),
                        }
                    })
                else:
                    return self._respond_text(text='Contacts not changed.', extra={
                        'template': 'Contacts not changed: ${ID}.',
                        'replacements': {
                            'ID': str(sender),
                        }
                    })
        else:
            return self._respond_text(text='Command not support.', extra={
                'template': 'Storage command (title: ${title}) not support yet!',
                'replacements': {
                    'title': title,
                }
            })
