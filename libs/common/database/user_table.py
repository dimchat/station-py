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

from dimp import ID, Command

from .storage import Storage


class UserTable(Storage):

    def __init__(self):
        super().__init__()
        # caches
        self.__contacts = {}
        # stored commands
        self.__contacts_commands = {}
        self.__block_commands = {}
        self.__mute_commands = {}

    """
        User contacts
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts.txt'
    """
    def __contacts_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'contacts.txt')

    def __cache_contacts(self, contacts: list, identifier: ID) -> bool:
        assert identifier.is_user, 'user ID error: %s' % identifier
        if contacts is None:
            return False
        self.__contacts[identifier] = contacts
        return True

    def __load_contacts(self, identifier: ID) -> list:
        path = self.__contacts_path(identifier=identifier)
        self.info('Loading contacts from: %s' % path)
        data = self.read_text(path=path)
        if data is not None and len(data) > 1:
            return data.splitlines()

    def __save_contacts(self, contacts: list, identifier: ID) -> bool:
        path = self.__contacts_path(identifier=identifier)
        self.info('Saving contacts into: %s' % path)
        text = '\n'.join(contacts)
        return self.write_text(text=text, path=path)

    def contacts(self, user: ID) -> list:
        array = self.__contacts.get(user)
        if array is not None:
            return array
        array = self.__load_contacts(identifier=user)
        if self.__cache_contacts(contacts=array, identifier=user):
            return array

    def save_contacts(self, contacts: list, user: ID) -> bool:
        if self.__cache_contacts(contacts=contacts, identifier=user):
            return self.__save_contacts(contacts=contacts, identifier=user)

    """
        Contacts Command
        ~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts_stored.js'
    """
    def __contacts_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'contacts_stored.js')

    def contacts_command(self, identifier: ID) -> Command:
        cmd = self.__contacts_commands.get(identifier)
        if cmd is None:
            path = self.__contacts_command_path(identifier=identifier)
            self.info('Loading stored contacts command from: %s' % path)
            dictionary = self.read_json(path=path)
            if dictionary is not None:
                cmd = Command(dictionary)
                self.__contacts_commands[identifier] = cmd
        return cmd

    def save_contacts_command(self, cmd: Command, sender: ID) -> bool:
        assert cmd is not None, 'contacts command cannot be empty'
        self.__contacts_commands[sender] = cmd
        path = self.__contacts_command_path(identifier=sender)
        self.info('Saving contacts command into: %s' % path)
        return self.write_json(container=cmd, path=path)

    """
        Block Command
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/block_stored.js'
    """
    def __block_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'block_stored.js')

    def block_command(self, identifier: ID) -> Command:
        cmd = self.__block_commands.get(identifier)
        if cmd is None:
            path = self.__block_command_path(identifier=identifier)
            self.info('Loading stored block command from: %s' % path)
            dictionary = self.read_json(path=path)
            if dictionary is not None:
                cmd = Command(dictionary)
                self.__block_commands[identifier] = cmd
        return cmd

    def save_block_command(self, cmd: Command, sender: ID) -> bool:
        assert cmd is not None, 'block command cannot be empty'
        self.__block_commands[sender] = cmd
        path = self.__block_command_path(identifier=sender)
        self.info('Saving block command into: %s' % path)
        return self.write_json(container=cmd, path=path)

    """
        Mute Command
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/mute_stored.js'
    """
    def __mute_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'mute_stored.js')

    def mute_command(self, identifier: ID) -> Command:
        cmd = self.__mute_commands.get(identifier)
        if cmd is None:
            path = self.__mute_command_path(identifier=identifier)
            self.info('Loading stored mute command from: %s' % path)
            dictionary = self.read_json(path=path)
            if dictionary is not None:
                cmd = Command(dictionary)
                self.__mute_commands[identifier] = cmd
        return cmd

    def save_mute_command(self, cmd: Command, sender: ID) -> bool:
        assert cmd is not None, 'mute command cannot be empty'
        self.__mute_commands[sender] = cmd
        path = self.__mute_command_path(identifier=sender)
        self.info('Saving mute command into: %s' % path)
        return self.write_json(container=cmd, path=path)
