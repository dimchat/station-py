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

from dimp import ID

from .storage import Storage


class GroupTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__members: dict = {}

    """
        Group members
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/members.txt'
    """
    def __members_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'members.txt')

    def cache_members(self, members: list, identifier: ID) -> bool:
        assert identifier.is_group, 'group ID error: %s' % identifier
        if members is None or len(members) == 0:
            return False
        self.__members[identifier] = members
        return True

    def __load_members(self, identifier: ID) -> list:
        path = self.__members_path(identifier=identifier)
        self.info('Loading members from: %s' % path)
        data = self.read_text(path=path)
        if data is not None:
            return data.splitlines()

    def __save_members(self, members: list, identifier: ID) -> bool:
        path = self.__members_path(identifier=identifier)
        self.info('Saving members into: %s' % path)
        text = '\n'.join(members)
        return self.write_text(text=text, path=path)

    def members(self, group: ID) -> list:
        array = self.__members.get(group)
        if array is not None:
            return array
        return self.__load_members(identifier=group)

    def save_members(self, members: list, group: ID) -> bool:
        if self.cache_members(members=members, identifier=group):
            return self.__save_members(members=members, identifier=group)

    def founder(self, group: ID) -> ID:
        pass

    def owner(self, group: ID) -> ID:
        pass
