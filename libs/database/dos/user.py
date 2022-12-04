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

from typing import Optional

from dimsdk import ID

from dimples.database.dos.base import template_replace
from dimples.database import UserStorage as SuperStorage

from ...common import MuteCommand
from ...common import BlockCommand
from ...common import StorageCommand


class UserStorage(SuperStorage):

    """
        Contacts Command
        ~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/contacts_stored.js'
    """
    contacts_command_path = '{PRIVATE}/{ADDRESS}/contacts_stored.js'

    def show_info(self):
        super().show_info()
        path3 = template_replace(self.contacts_command_path, 'PRIVATE', self._private)
        path4 = template_replace(self.block_command_path, 'PRIVATE', self._private)
        path5 = template_replace(self.mute_command_path, 'PRIVATE', self._private)
        print('!!!  contacts path: %s' % path3)
        print('!!! block cmd path: %s' % path4)
        print('!!!  mute cmd path: %s' % path5)

    def __contacts_command_path(self, identifier: ID) -> str:
        path = self.contacts_command_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    def save_contacts_command(self, content: StorageCommand, identifier: ID) -> bool:
        assert content is not None, 'contacts command cannot be empty'
        path = self.__contacts_command_path(identifier=identifier)
        self.info('Saving contacts command into: %s' % path)
        return self.write_json(container=content.dictionary, path=path)

    def contacts_command(self, identifier: ID) -> Optional[StorageCommand]:
        path = self.__contacts_command_path(identifier=identifier)
        self.info('Loading stored contacts command from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return StorageCommand(content=dictionary)

    """
        Block Command
        ~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/block_stored.js'
    """
    block_command_path = '{PRIVATE}/{ADDRESS}/block_stored.js'

    def __block_command_path(self, identifier: ID) -> str:
        path = self.block_command_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    def save_block_command(self, content: BlockCommand, identifier: ID) -> bool:
        assert content is not None, 'block command cannot be empty'
        path = self.__block_command_path(identifier=identifier)
        self.info('Saving block command into: %s' % path)
        return self.write_json(container=content.dictionary, path=path)

    def block_command(self, identifier: ID) -> Optional[BlockCommand]:
        path = self.__block_command_path(identifier=identifier)
        self.info('Loading stored block command from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return BlockCommand(content=dictionary)

    """
        Mute Command
        ~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/mute_stored.js'
    """
    mute_command_path = '{PRIVATE}/{ADDRESS}/mute_stored.js'

    def __mute_command_path(self, identifier: ID) -> str:
        path = self.mute_command_path
        path = template_replace(path, 'PRIVATE', self._private)
        return template_replace(path, 'ADDRESS', str(identifier.address))

    def save_mute_command(self, content: MuteCommand, identifier: ID) -> bool:
        assert content is not None, 'mute command cannot be empty'
        path = self.__mute_command_path(identifier=identifier)
        self.info('Saving mute command into: %s' % path)
        return self.write_json(container=content.dictionary, path=path)

    def mute_command(self, identifier: ID) -> Optional[MuteCommand]:
        path = self.__mute_command_path(identifier=identifier)
        self.info('Loading stored mute command from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return MuteCommand(content=dictionary)
