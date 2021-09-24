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

from typing import List, Dict

from dimp import ID

from .redis import GroupCache
from .dos import GroupStorage

from .cache import CacheHolder, CachePool


class GroupTable:

    def __init__(self):
        super().__init__()
        self.__redis = GroupCache()
        self.__dos = GroupStorage()
        # memory caches
        self.__caches: Dict[ID, CacheHolder[List[ID]]] = CachePool.get_caches('members')

    def save_members(self, members: List[ID], group: ID) -> bool:
        # 1. save to memory cache
        self.__caches[group] = CacheHolder(value=members)
        # 2. save to redis server
        self.__redis.save_members(members=members, group=group)
        # 3. save to local storage
        return self.__dos.save_members(members=members, group=group)

    def members(self, group: ID) -> List[ID]:
        # 1. check memory cache
        holder = self.__caches.get(group)
        if holder is not None and holder.alive:
            return holder.value
        else:  # place an empty holder to avoid frequent reading
            self.__caches[group] = CacheHolder(value=[], life_span=16)
        # 2. check redis server
        array = self.__redis.members(group=group)
        if array is not None and len(array) > 0:
            # update memory cache
            self.__caches[group] = CacheHolder(value=array)
            return array
        # 3. check local storage
        array = self.__dos.members(group=group)
        if array is not None and len(array) > 0:
            # update memory cache & redis server
            self.__caches[group] = CacheHolder(value=array)
            self.__redis.save_members(members=array, group=group)
            return array
        # member not found
        return []

    def founder(self, group: ID) -> ID:
        # TODO: get founder
        pass

    def owner(self, group: ID) -> ID:
        # TODO: get owner
        pass
