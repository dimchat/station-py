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
from typing import Optional, Union, Set, Dict

from aiou.mem import CachePool
from aiou.mem.cache import V

from dimples import DateTime
from dimples import ID
from dimples.utils import SharedCacheManager
from dimples.database import DbInfo, DbTask

from .redis import AddressNameCache
from .dos import AddressNameStorage


# noinspection PyAbstractClass
class AnsTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self,
                 cache_pool: CachePool, redis: AddressNameCache, storage: AddressNameStorage,
                 mutex_lock: Union[threading.Lock, threading.RLock]):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._redis = redis
        self._dos = storage

    # Override
    async def _load_redis_cache(self) -> Optional[V]:
        pass

    # Override
    async def _save_redis_cache(self, value: V) -> bool:
        pass

    # Override
    async def _load_local_storage(self) -> Optional[V]:
        pass

    # Override
    async def _save_local_storage(self, value: V) -> bool:
        pass


class AllTask(AnsTask):

    ALL_KEY = 'all_records'

    # Override
    def cache_key(self) -> str:
        return self.ALL_KEY

    # Override
    async def _load_local_storage(self) -> Optional[Dict[str, ID]]:
        return await self._dos.load_records()


class IdTask(AnsTask):

    def __init__(self, name: str,
                 cache_pool: CachePool, redis: AddressNameCache, storage: AddressNameStorage,
                 mutex_lock: Union[threading.Lock, threading.RLock]):
        super().__init__(cache_pool=cache_pool, redis=redis, storage=storage, mutex_lock=mutex_lock)
        self._name = name

    # Override
    def cache_key(self) -> str:
        return self._name

    # Override
    async def _load_redis_cache(self) -> Optional[ID]:
        return await self._redis.get_record(name=self._name)


class NameTask(AnsTask):

    def __init__(self, identifier: ID,
                 cache_pool: CachePool, redis: AddressNameCache, storage: AddressNameStorage,
                 mutex_lock: Union[threading.Lock, threading.RLock]):
        super().__init__(cache_pool=cache_pool, redis=redis, storage=storage, mutex_lock=mutex_lock)
        self._identifier = identifier

    # Override
    def cache_key(self) -> ID:
        return self._identifier

    # Override
    async def _load_redis_cache(self) -> Optional[Set[str]]:
        return await self._redis.get_names(identifier=self._identifier)


class AddressNameTable:

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='ans')  # str => ID
        self._redis = AddressNameCache(connector=info.redis_connector)
        self._dos = AddressNameStorage(root=info.root_dir, public=info.public_dir, private=info.private_dir)
        self._lock = threading.RLock()

    def show_info(self):
        self._dos.show_info()

    def _new_all_task(self) -> AllTask:
        return AllTask(cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    def _new_id_task(self, name: str) -> IdTask:
        return IdTask(name=name,
                      cache_pool=self._cache, redis=self._redis, storage=self._dos,
                      mutex_lock=self._lock)

    def _new_name_task(self, identifier: ID) -> NameTask:
        return NameTask(identifier=identifier,
                        cache_pool=self._cache, redis=self._redis, storage=self._dos,
                        mutex_lock=self._lock)

    async def _load_records(self) -> Dict[str, ID]:
        task = self._new_all_task()
        records = await task.load()
        return {} if records is None else records

    async def save_record(self, name: str, identifier: ID) -> bool:
        now = DateTime.current_timestamp()
        with self._lock:
            #
            #  1. update memory cache
            #
            if identifier is not None:
                # remove: ID => Set[str]
                self._cache.erase(key=identifier)
            all_records = await self._load_records()
            all_records[name] = identifier
            self._cache.update(key=AllTask.ALL_KEY, value=all_records, life_span=AnsTask.MEM_CACHE_EXPIRES, now=now)
            #
            #  2. update redis server
            #
            await self._redis.save_record(name=name, identifier=identifier)
            #
            #  3. update local storage
            #
            return await self._dos.save_records(records=all_records)

    async def get_record(self, name: str) -> Optional[ID]:
        #
        #  1. get record with name
        #
        task = self._new_id_task(name=name)
        did = await task.load()
        if isinstance(did, ID):
            return did
        #
        #  2. load all records
        #
        task = self._new_all_task()
        all_records = await task.load()
        if isinstance(all_records, Dict):
            did = all_records.get(name)
        #
        #   3. update memory cache
        #
        with self._lock:
            if did is not None:
                await self._redis.save_record(name=name, identifier=did)
            self._cache.update(key=name, value=did, life_span=AnsTask.MEM_CACHE_EXPIRES)
        return did

    async def get_names(self, identifier: ID) -> Set[str]:
        #
        #  1. get names for id
        #
        task = self._new_name_task(identifier=identifier)
        names = await task.load()
        if isinstance(names, Set):
            return names
        #
        #  2. load all records
        #
        task = self._new_all_task()
        all_records = await task.load()
        if isinstance(all_records, Dict):
            names = get_names(records=all_records, identifier=identifier)
        else:
            names = set()
        #
        #   3. update memory cache
        #
        with self._lock:
            self._cache.update(key=identifier, value=names, life_span=AnsTask.MEM_CACHE_EXPIRES)
        return names


def get_names(records: Dict[str, ID], identifier: ID) -> Set[str]:
    strings = set()
    for key in records:
        if identifier == records[key]:
            strings.add(key)
    return strings
