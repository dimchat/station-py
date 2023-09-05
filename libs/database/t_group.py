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
from typing import List

from dimples import ID

from dimples.utils import CacheManager
from dimples import GroupDBI

from .dos import GroupStorage
from .redis import GroupCache


class GroupTable(GroupDBI):
    """ Implementations of GroupDBI """

    CACHE_EXPIRES = 300    # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = GroupStorage(root=root, public=public, private=private)
        self.__redis = GroupCache()
        man = CacheManager()
        self.__members_cache = man.get_pool(name='group.members')                # ID => List[ID]
        self.__assistants_cache = man.get_pool(name='group.assistants')          # ID => List[ID]
        self.__administrators_cache = man.get_pool(name='group.administrators')  # ID => List[ID]

    def show_info(self):
        self.__dos.show_info()

    #
    #   Group DBI
    #

    # Override
    def members(self, group: ID) -> List[ID]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__members_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__members_cache.update(key=group, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return []
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.members(group=group)
            if value is None:
                # 3. check local storage
                value = self.__dos.members(group=group)
                # update redis server
                self.__redis.save_members(members=value, group=group)
            # update memory cache
            self.__members_cache.update(key=group, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def save_members(self, members: List[ID], group: ID) -> bool:
        # 1. store into memory cache
        self.__members_cache.update(key=group, value=members, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_members(members=members, group=group)
        # 3. store into local storage
        return self.__dos.save_members(members=members, group=group)

    # Override
    def assistants(self, group: ID) -> List[ID]:
        """ get assistants of group """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__assistants_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__assistants_cache.update(key=group, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return []
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.assistants(group=group)
            if value is None:
                # 3. check local storage
                value = self.__dos.assistants(group=group)
                # update redis server
                self.__redis.save_assistants(assistants=value, group=group)
            # update memory cache
            self.__assistants_cache.update(key=group, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        # 1. store into memory cache
        self.__assistants_cache.update(key=group, value=assistants, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_assistants(assistants=assistants, group=group)
        # 3. store into local storage
        return self.__dos.save_assistants(assistants=assistants, group=group)

    # Override
    def administrators(self, group: ID) -> List[ID]:
        """ get administrators of group """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__administrators_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__administrators_cache.update(key=group, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return []
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.administrators(group=group)
            if value is None:
                # 3. check local storage
                value = self.__dos.administrators(group=group)
                # update redis server
                self.__redis.save_administrators(administrators=value, group=group)
            # update memory cache
            self.__administrators_cache.update(key=group, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def save_administrators(self, administrators: List[ID], group: ID) -> bool:
        # 1. store into memory cache
        self.__administrators_cache.update(key=group, value=administrators, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_administrators(administrators=administrators, group=group)
        # 3. store into local storage
        return self.__dos.save_administrators(administrators=administrators, group=group)
