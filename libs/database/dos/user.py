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

import os
from typing import List, Optional

from dimsdk import ID, Command, BaseCommand

from .base import Storage


class UserStorage(Storage):
    """
        User contacts
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts.txt'
    """
    def __contacts_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'contacts.txt')

    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        assert contacts is not None, 'contacts cannot be empty'
        path = self.__contacts_path(identifier=user)
        self.info('Saving contacts into: %s' % path)
        contacts = ID.revert(members=contacts)
        text = '\n'.join(contacts)
        return self.write_text(text=text, path=path)

    def contacts(self, user: ID) -> List[ID]:
        path = self.__contacts_path(identifier=user)
        self.info('Loading contacts from: %s' % path)
        text = self.read_text(path=path)
        if text is None:
            return []
        return ID.convert(members=text.splitlines())

    """
        Contacts Command
        ~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts_stored.js'
    """
    def __contacts_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'contacts_stored.js')

    def save_contacts_command(self, content: Command, sender: ID) -> bool:
        assert content is not None, 'contacts command cannot be empty'
        path = self.__contacts_command_path(identifier=sender)
        self.info('Saving contacts command into: %s' % path)
        return self.write_json(container=content.dictionary, path=path)

    def contacts_command(self, identifier: ID) -> Optional[Command]:
        path = self.__contacts_command_path(identifier=identifier)
        self.info('Loading stored contacts command from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return BaseCommand(content=dictionary)

    """
        Block Command
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/block_stored.js'
    """
    def __block_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'block_stored.js')

    def save_block_command(self, content: Command, sender: ID) -> bool:
        assert content is not None, 'block command cannot be empty'
        path = self.__block_command_path(identifier=sender)
        self.info('Saving block command into: %s' % path)
        return self.write_json(container=content.dictionary, path=path)

    def block_command(self, identifier: ID) -> Optional[Command]:
        path = self.__block_command_path(identifier=identifier)
        self.info('Loading stored block command from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return BaseCommand(content=dictionary)

    """
        Mute Command
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/mute_stored.js'
    """
    def __mute_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'mute_stored.js')

    def save_mute_command(self, content: Command, sender: ID) -> bool:
        assert content is not None, 'mute command cannot be empty'
        path = self.__mute_command_path(identifier=sender)
        self.info('Saving mute command into: %s' % path)
        return self.write_json(container=content.dictionary, path=path)

    def mute_command(self, identifier: ID) -> Optional[Command]:
        path = self.__mute_command_path(identifier=identifier)
        self.info('Loading stored mute command from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return BaseCommand(content=dictionary)
