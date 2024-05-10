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

from typing import Optional, List

from dimples import utf8_encode, utf8_decode
from dimples import ID

from .base import Cache


class GroupCache(Cache):

    # group info cached in Redis will be removed after 30 minutes, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 1800  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def tbl_name(self) -> str:
        return 'group'

    """
        Group members
        ~~~~~~~~~~~~~

        redis key: 'mkm.group.{ID}.members'
    """
    def __members_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.members' % (self.db_name, self.tbl_name, identifier)

    async def get_members(self, group: ID) -> Optional[List[ID]]:
        key = self.__members_cache_name(identifier=group)
        value = self.get(name=key)
        if value is not None:
            text = utf8_decode(data=value)
            assert text is not None, 'failed to decode string: %s' % value
            return ID.convert(array=text.splitlines())

    async def save_members(self, members: List[ID], group: ID) -> bool:
        users = ID.revert(array=members)
        text = '\n'.join(users)
        value = utf8_encode(string=text)
        key = self.__members_cache_name(identifier=group)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    """
        Group administrators
        ~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.group.{ID}.administrators'
    """
    def __administrators_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.administrators' % (self.db_name, self.tbl_name, identifier)

    async def get_administrators(self, group: ID) -> Optional[List[ID]]:
        key = self.__administrators_cache_name(identifier=group)
        value = self.get(name=key)
        if value is not None:
            text = utf8_decode(data=value)
            assert text is not None, 'failed to decode string: %s' % value
            return ID.convert(array=text.splitlines())

    async def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        users = ID.revert(array=administrators)
        text = '\n'.join(users)
        value = utf8_encode(string=text)
        key = self.__administrators_cache_name(identifier=group)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    """
        Group assistants
        ~~~~~~~~~~~~~~~~

        redis key: 'mkm.group.{ID}.assistants'
    """
    def __assistants_cache_name(self, identifier: ID) -> str:
        return '%s.%s.%s.assistants' % (self.db_name, self.tbl_name, identifier)

    async def get_assistants(self, group: ID) -> Optional[List[ID]]:
        key = self.__assistants_cache_name(identifier=group)
        value = self.get(name=key)
        if value is not None:
            text = utf8_decode(data=value)
            assert text is not None, 'failed to decode string: %s' % value
            return ID.convert(array=text.splitlines())

    async def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        bots = ID.revert(array=assistants)
        text = '\n'.join(bots)
        value = utf8_encode(string=text)
        key = self.__assistants_cache_name(identifier=group)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True
