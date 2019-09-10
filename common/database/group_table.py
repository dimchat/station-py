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
        self.__caches = {}

    """
        Group members
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/members.txt'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', identifier.address, 'members.txt')

    def __cache_members(self, members: list, identifier: ID) -> bool:
        if members is None or len(members) == 0:
            return False
        assert identifier.valid, 'ID not valid: %s' % identifier
        self.__caches[identifier] = members
        return True

    def __load_members(self, identifier: ID) -> list:
        path = self.__path(identifier=identifier)
        self.info('Loading members from: %s' % path)
        data = self.read_text(path=path)
        if data is not None:
            return data.splitlines()

    def __save_members(self, members: list, identifier: ID) -> bool:
        path = self.__path(identifier=identifier)
        self.info('Saving members into: %s' % path)
        text = '\n'.join(members)
        return self.write_text(text=text, path=path)

    def members(self, group: ID) -> list:
        array = self.__caches.get(group)
        if array is not None:
            return array
        array = self.__load_members(identifier=group)
        if self.__cache_members(members=array, identifier=group):
            return array

    def save_members(self, members: list, group: ID) -> bool:
        if self.__cache_members(members=members, identifier=group):
            return self.__save_members(members=members, identifier=group)
