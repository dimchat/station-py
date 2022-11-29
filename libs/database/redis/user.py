# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from typing import List, Optional

from dimsdk import utf8_encode, utf8_decode, json_encode, json_decode
from dimsdk import ID, Command

from .base import Cache


class UserCache(Cache):

    # user info cached in Redis will be removed after 10 hours, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 36000  # seconds

    @property  # Override
    def database(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def table(self) -> str:
        return 'user'

    """
        User contacts
        ~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.contacts'
    """
    def __contacts_key(self, identifier: ID) -> str:
        return '%s.%s.%s.contacts' % (self.database, self.table, identifier)

    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        assert contacts is not None, 'contacts cannot be empty'
        contacts = ID.revert(members=contacts)
        text = '\n'.join(contacts)
        text = utf8_encode(string=text)
        key = self.__contacts_key(identifier=user)
        self.set(name=key, value=text, expires=self.EXPIRES)
        return True

    def contacts(self, user: ID) -> List[ID]:
        key = self.__contacts_key(identifier=user)
        value = self.get(name=key)
        if value is None:
            return []
        text = utf8_decode(data=value)
        return ID.convert(members=text.splitlines())

    """
        Contacts Command
        ~~~~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.cmd.contacts'
    """
    def __contacts_command_key(self, identifier: ID) -> str:
        return '%s.%s.%s.cmd.contacts' % (self.database, self.table, identifier)

    def save_contacts_command(self, content: Command, sender: ID) -> bool:
        key = self.__contacts_command_key(identifier=sender)
        return self.__save_command(key=key, content=content)

    def contacts_command(self, identifier: ID) -> Optional[Command]:
        key = self.__contacts_command_key(identifier=identifier)
        return self.__load_command(key=key)

    def __save_command(self, key: str, content: Command) -> bool:
        dictionary = content.dictionary
        value = json_encode(obj=dictionary)
        value = utf8_encode(string=value)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def __load_command(self, key: str) -> Optional[Command]:
        value = self.get(name=key)
        if value is None:
            return None
        value = utf8_decode(data=value)
        dictionary = json_decode(string=value)
        assert dictionary is not None, 'cmd error: %s' % value
        # return BaseCommand(content=dictionary)
        return Command.parse(content=dictionary)

    """
        Block Command
        ~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.cmd.block'
    """
    def __block_command_key(self, identifier: ID) -> str:
        return '%s.%s.%s.cmd.block' % (self.database, self.table, identifier)

    def save_block_command(self, content: Command, sender: ID) -> bool:
        key = self.__block_command_key(identifier=sender)
        return self.__save_command(key=key, content=content)

    def block_command(self, identifier: ID) -> Optional[Command]:
        key = self.__block_command_key(identifier=identifier)
        return self.__load_command(key=key)

    """
        Mute Command
        ~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.cmd.mute'
    """
    def __mute_command_key(self, identifier: ID) -> str:
        return '%s.%s.%s.cmd.mute' % (self.database, self.table, identifier)

    def save_mute_command(self, content: Command, sender: ID) -> bool:
        key = self.__mute_command_key(identifier=sender)
        return self.__save_command(key=key, content=content)

    def mute_command(self, identifier: ID) -> Optional[Command]:
        key = self.__mute_command_key(identifier=identifier)
        return self.__load_command(key=key)
