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

import threading
from typing import Dict, Set, Tuple, Optional

from aiou.mem import CachePool

from dimples import ID
from dimples.utils import SharedCacheManager
from dimples.database import DbInfo, DbTask

from .redis import LoginCache


class ActTask(DbTask):

    MEM_CACHE_EXPIRES = 60  # seconds
    MEM_CACHE_REFRESH = 8   # seconds

    def __init__(self,
                 cache_pool: CachePool, redis: LoginCache,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._redis = redis

    # Override
    def cache_key(self) -> str:
        return 'active_users'

    # Override
    async def _load_redis_cache(self) -> Optional[Set[ID]]:
        users = await self._redis.get_active_users()
        if users is None or len(users) == 0:
            return None
        else:
            return users

    # Override
    async def _save_redis_cache(self, value: Set[ID]) -> bool:
        pass

    # Override
    async def _load_local_storage(self) -> Optional[Set[ID]]:
        pass

    # Override
    async def _save_local_storage(self, value: Set[ID]) -> bool:
        pass


class ActiveTable:

    def __init__(self, info: DbInfo):
        super().__init__()
        self._socket_address: Dict[ID, Set[Tuple[str, int]]] = {}  # ID => set(socket_address)
        man = SharedCacheManager()
        self._cache = man.get_pool(name='session')  # 'active_users' => Set(ID)
        self._redis = LoginCache(connector=info.redis_connector)
        self._lock = threading.Lock()

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!    active users in memory only !!!')

    def _new_task(self) -> ActTask:
        return ActTask(cache_pool=self._cache, redis=self._redis,
                       mutex_lock=self._lock)

    async def clear_socket_addresses(self):
        """ clear before station start """
        with self._lock:
            self._cache.erase(key='active_users')
            await self._redis.clear_socket_addresses()

    async def get_active_users(self) -> Set[ID]:
        """ read by archivist bot """
        task = self._new_task()
        users = await task.load()
        return set() if users is None else users

    async def add_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        """ wrote by station only """
        with self._lock:
            # 1. add into local cache
            sockets = self._socket_address.get(identifier)
            if sockets is None:
                sockets = set()
                self._socket_address[identifier] = sockets
            sockets.add(address)
            # 2. store into Redis Server
            await self._redis.save_socket_addresses(identifier=identifier, addresses=sockets)
            return sockets

    async def remove_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        """ wrote by station only """
        with self._lock:
            # 1. remove from local cache
            sockets = self._socket_address.get(identifier)
            if sockets is not None:
                sockets.discard(address)
                if len(sockets) == 0:
                    self._socket_address.pop(identifier, None)
                    sockets = None
            # 2. store into Redis Server
            await self._redis.save_socket_addresses(identifier=identifier, addresses=sockets)
            return sockets
