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

from typing import Dict, Set, Tuple

from dimples import DateTime
from dimples import ID

from dimples.utils import CacheManager

from .redis import LoginCache


class ActiveTable:

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__redis = LoginCache()
        self.__cache: Dict[ID, Set[Tuple[str, int]]] = {}  # ID => set(socket_address)
        man = CacheManager()
        self.__active_cache = man.get_pool(name='session')  # 'active_users' => Set(ID)

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!    active users in memory only !!!')

    async def clear_socket_addresses(self):
        """ clear before station start """
        self.__active_cache.erase(key='active_users')
        await self.__redis.clear_socket_addresses()

    async def get_active_users(self) -> Set[ID]:
        """ read by archivist bot """
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__active_cache.fetch(key='active_users', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # active_users not load yet, wait to load
                self.__active_cache.update(key='active_users', life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # active_users not exists
                    return set()
                # active_users expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = await self.__redis.get_active_users()
            # 3. update memory cache
            self.__active_cache.update(key='active_users', value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    async def add_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        """ wrote by station only """
        # 1. add into local cache
        sockets = self.__cache.get(identifier)
        if sockets is None:
            sockets = set()
            self.__cache[identifier] = sockets
        sockets.add(address)
        # 2. store into Redis Server
        await self.__redis.save_socket_addresses(identifier=identifier, addresses=sockets)
        return sockets

    async def remove_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        """ wrote by station only """
        # 1. remove from local cache
        sockets = self.__cache.get(identifier)
        if sockets is not None:
            sockets.discard(address)
            if len(sockets) == 0:
                self.__cache.pop(identifier, None)
        # 2. store into Redis Server
        await self.__redis.save_socket_addresses(identifier=identifier, addresses=sockets)
        return sockets
