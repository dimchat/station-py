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

    """
        Contacts Command
        ~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts_stored.js'
    """
    def __contacts_command_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', identifier.address, 'contacts_stored.js')

    def __load_contacts_command(self, identifier: ID) -> Command:
        path = self.__contacts_command_path(identifier=identifier)
        self.info('Loading stored contacts command from: %s' % path)
        dictionary = self.read_json(path=path)
        return Command(dictionary)

    def __save_contacts_command(self, cmd: Command, identifier: ID) -> bool:
        path = self.__contacts_command_path(identifier=identifier)
        self.info('Saving contacts command into: %s' % path)
        return self.write_json(container=cmd, path=path)

    def contacts_command(self, identifier: ID) -> Command:
        return self.__load_contacts_command(identifier=identifier)

    def save_contacts_command(self, cmd: Command, sender: ID) -> bool:
        identifier = cmd.get('ID')
        if identifier is not None and identifier != sender:
            return False
        if 'data' not in cmd and 'contacts' not in cmd:
            return False
        return self.__save_contacts_command(cmd=cmd, identifier=sender)
