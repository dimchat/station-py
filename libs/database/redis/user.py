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

from dimples import utf8_encode, utf8_decode, json_encode, json_decode
from dimples import ID, Content, Command

from ...common import BlockCommand, MuteCommand

from .base import Cache


class UserCache(Cache):

    # user info cached in Redis will be removed after 30 minutes, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 1800  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def tbl_name(self) -> str:
        return 'user'

    """
        User contacts
        ~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.contacts'
    """
    def __contacts_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.contacts' % (self.db_name, self.tbl_name, identifier)

    async def save_contacts(self, contacts: List[ID], identifier: ID) -> bool:
        assert contacts is not None, 'contacts cannot be empty'
        contacts = ID.revert(array=contacts)
        text = '\n'.join(contacts)
        text = utf8_encode(string=text)
        key = self.__contacts_cache_name(identifier=identifier)
        self.set(name=key, value=text, expires=self.EXPIRES)
        return True

    async def get_contacts(self, identifier: ID) -> List[ID]:
        key = self.__contacts_cache_name(identifier=identifier)
        value = self.get(name=key)
        if value is None:
            return []
        text = utf8_decode(data=value)
        return ID.convert(array=text.splitlines())

    """
        Contacts Command
        ~~~~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.cmd.contacts'
    """
    def __contacts_command_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.cmd.contacts' % (self.db_name, self.tbl_name, identifier)

    async def save_contacts_command(self, content: Command, identifier: ID) -> bool:
        key = self.__contacts_command_cache_name(identifier=identifier)
        return self.__save_command(key=key, content=content)

    async def get_contacts_command(self, identifier: ID) -> Optional[Command]:
        key = self.__contacts_command_cache_name(identifier=identifier)
        dictionary = self.__load_command(key=key)
        if dictionary is not None:
            return Content.parse(content=dictionary)  # -> StorageCommand

    def __save_command(self, key: str, content: Command) -> bool:
        dictionary = content.dictionary
        js = json_encode(obj=dictionary)
        value = utf8_encode(string=js)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def __load_command(self, key: str) -> Optional[dict]:
        value = self.get(name=key)
        if value is None:
            return None
        js = utf8_decode(data=value)
        dictionary = json_decode(string=js)
        assert dictionary is not None, 'cmd error: %s' % value
        return dictionary

    """
        Block Command
        ~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.cmd.block'
    """
    def __block_command_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.cmd.block' % (self.db_name, self.tbl_name, identifier)

    async def save_block_command(self, content: BlockCommand, identifier: ID) -> bool:
        key = self.__block_command_cache_name(identifier=identifier)
        return self.__save_command(key=key, content=content)

    async def get_block_command(self, identifier: ID) -> Optional[BlockCommand]:
        key = self.__block_command_cache_name(identifier=identifier)
        dictionary = self.__load_command(key=key)
        if dictionary is not None:
            return BlockCommand(content=dictionary)

    """
        Mute Command
        ~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.cmd.mute'
    """
    def __mute_command_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.cmd.mute' % (self.db_name, self.tbl_name, identifier)

    async def save_mute_command(self, content: MuteCommand, identifier: ID) -> bool:
        key = self.__mute_command_cache_name(identifier=identifier)
        return self.__save_command(key=key, content=content)

    async def get_mute_command(self, identifier: ID) -> Optional[MuteCommand]:
        key = self.__mute_command_cache_name(identifier=identifier)
        dictionary = self.__load_command(key=key)
        if dictionary is not None:
            return MuteCommand(content=dictionary)
