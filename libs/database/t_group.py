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

import time
from typing import Optional, List

from dimples import ID

from dimples.utils import CacheHolder, CacheManager
from dimples.common import GroupDBI

from .redis import GroupCache
from .dos import GroupStorage


class GroupTable(GroupDBI):
    """ Implementations of GroupDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = GroupStorage(root=root, public=public, private=private)
        self.__redis = GroupCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='members')  # ID => List[ID]

    def show_info(self):
        self.__dos.show_info()

    #
    #   Group DBI
    #

    # Override
    def founder(self, identifier: ID) -> Optional[ID]:
        # TODO: get founder
        pass

    # Override
    def owner(self, identifier: ID) -> Optional[ID]:
        # TODO: get owner
        pass

    # Override
    def save_members(self, members: List[ID], identifier: ID) -> bool:
        # 1. store into memory cache
        self.__cache.update(key=identifier, value=members, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_members(members=members, identifier=identifier)
        # 3. store into local storage
        return self.__dos.save_members(members=members, identifier=identifier)

    # Override
    def members(self, identifier: ID) -> List[ID]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # meta not load yet, wait to load
                self.__cache.update(key=identifier, life_span=self.CACHE_REFRESHING, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'meta cache error'
                if holder.is_alive(now=now):
                    # meta not exists
                    return []
                # meta expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.members(identifier=identifier)
            if len(value) == 0:
                # 3. check local storage
                value = self.__dos.members(identifier=identifier)
                if len(value) > 0:
                    # update redis server
                    self.__redis.save_members(members=value, identifier=identifier)
            # update memory cache
            self.__cache.update(key=identifier, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def save_assistants(self, assistants: List[ID], identifier: ID) -> bool:
        # TODO: save assistants
        pass

    # Override
    def assistants(self, identifier: ID) -> List[ID]:
        # TODO: get assistants
        pass
