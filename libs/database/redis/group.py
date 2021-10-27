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

from typing import Optional, List, Dict

from dimp import utf8_encode, utf8_decode, json_encode, json_decode
from dimp import ID

from .base import Cache


class GroupCache(Cache):

    # group info cached in Redis will be removed after 10 hours, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 36000  # seconds

    @property  # Override
    def database(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def table(self) -> str:
        return 'group'

    """
        Group members
        ~~~~~~~~~~~~~

        redis key: 'mkm.group.{ID}.members'
    """
    def __members_key(self, identifier: ID) -> str:
        return '%s.%s.%s.members' % (self.database, self.table, identifier)

    def save_members(self, members: List[ID], group: ID) -> bool:
        members = ID.revert(members=members)
        text = '\n'.join(members)
        value = utf8_encode(string=text)
        key = self.__members_key(identifier=group)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def members(self, group: ID) -> List[ID]:
        key = self.__members_key(identifier=group)
        value = self.get(name=key)
        if value is None:
            return []
        text = utf8_decode(data=value)
        return ID.convert(members=text.splitlines())

    def founder(self, group: ID) -> ID:
        # TODO: get founder
        pass

    def owner(self, group: ID) -> ID:
        # TODO: get owner
        pass

    """
        Encrypted keys
        ~~~~~~~~~~~~~~

        redis key: 'mkm.group.{GID}.encrypted-keys'
    """
    def __keys_name(self, group: ID) -> str:
        return '%s.%s.%s.encrypted-keys' % (self.database, self.table, group)

    def save_keys(self, keys: Dict[str, str], sender: ID, group: ID) -> bool:
        name = self.__keys_name(group=group)
        key = str(sender)
        value = json_encode(o=keys)
        self.hset(name=name, key=key, value=value)
        return True

    def load_keys(self, sender: ID, group: ID) -> Optional[Dict[str, str]]:
        name = self.__keys_name(group=group)
        key = str(sender)
        value = self.hget(name=name, key=key)
        if value is not None and len(value) > 2:
            return json_decode(data=value)
