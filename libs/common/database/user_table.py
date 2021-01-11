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

from dimp import ID, Command

from .storage import Storage


class UserTable(Storage):

    def __init__(self):
        super().__init__()
        # caches
        self.__contacts = {}           # ID -> List[ID]
        # stored commands
        self.__contacts_commands = {}  # ID -> Command
        self.__block_commands = {}     # ID -> Command
        self.__mute_commands = {}      # ID -> Command
        self.__empty = {'desc': 'just to avoid loading non-exists file again'}

    """
        User contacts
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts.txt'
    """
    def __contacts_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'contacts.txt')

    def contacts(self, user: ID) -> List[ID]:
        # try from memory cache
        array = self.__contacts.get(user)
        if array is None:
            # try from local storage
            path = self.__contacts_path(identifier=user)
            self.info('Loading contacts from: %s' % path)
            text = self.read_text(path=path)
            if text is None:
                array = []
            else:
                array = ID.convert(members=text.splitlines())
            # store into memory cache
            self.__contacts[user] = array
        return array

    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        assert contacts is not None, 'contacts cannot be empty'
        # store into memory cache
        self.__contacts[user] = contacts
        # store into local storage
        path = self.__contacts_path(identifier=user)
        self.info('Saving contacts into: %s' % path)
        contacts = ID.revert(members=contacts)
        text = '\n'.join(contacts)
        return self.write_text(text=text, path=path)

    """
        Contacts Command
        ~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts_stored.js'
    """
    def __contacts_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'contacts_stored.js')

    def contacts_command(self, identifier: ID) -> Optional[Command]:
        # try from memory cache
        cmd = self.__contacts_commands.get(identifier)
        if cmd is None:
            # try from local storage
            path = self.__contacts_command_path(identifier=identifier)
            self.info('Loading stored contacts command from: %s' % path)
            dictionary = self.read_json(path=path)
            if dictionary is None:
                cmd = self.__empty
            else:
                cmd = Command(dictionary)
            self.__contacts_commands[identifier] = cmd
        if cmd is not self.__empty:
            return cmd

    def save_contacts_command(self, cmd: Command, sender: ID) -> bool:
        assert cmd is not None, 'contacts command cannot be empty'
        # store into memory cache
        self.__contacts_commands[sender] = cmd
        # store into local storage
        path = self.__contacts_command_path(identifier=sender)
        self.info('Saving contacts command into: %s' % path)
        return self.write_json(container=cmd.dictionary, path=path)

    """
        Block Command
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/block_stored.js'
    """
    def __block_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'block_stored.js')

    def block_command(self, identifier: ID) -> Command:
        # try from memory cache
        cmd = self.__block_commands.get(identifier)
        if cmd is None:
            # try from local storage
            path = self.__block_command_path(identifier=identifier)
            self.info('Loading stored block command from: %s' % path)
            dictionary = self.read_json(path=path)
            if dictionary is None:
                cmd = self.__empty
            else:
                cmd = Command(dictionary)
            self.__block_commands[identifier] = cmd
        if cmd is not self.__empty:
            return cmd

    def save_block_command(self, cmd: Command, sender: ID) -> bool:
        assert cmd is not None, 'block command cannot be empty'
        # store into memory cache
        self.__block_commands[sender] = cmd
        # store into local storage
        path = self.__block_command_path(identifier=sender)
        self.info('Saving block command into: %s' % path)
        return self.write_json(container=cmd.dictionary, path=path)

    """
        Mute Command
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/mute_stored.js'
    """
    def __mute_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'mute_stored.js')

    def mute_command(self, identifier: ID) -> Command:
        # try from memory cache
        cmd = self.__mute_commands.get(identifier)
        if cmd is None:
            # try from local storage
            path = self.__mute_command_path(identifier=identifier)
            self.info('Loading stored mute command from: %s' % path)
            dictionary = self.read_json(path=path)
            if dictionary is None:
                cmd = self.__empty
            else:
                cmd = Command(dictionary)
            self.__mute_commands[identifier] = cmd
        if cmd is not self.__empty:
            return cmd

    def save_mute_command(self, cmd: Command, sender: ID) -> bool:
        assert cmd is not None, 'mute command cannot be empty'
        # store into memory cache
        self.__mute_commands[sender] = cmd
        # store into local storage
        path = self.__mute_command_path(identifier=sender)
        self.info('Saving mute command into: %s' % path)
        return self.write_json(container=cmd.dictionary, path=path)
