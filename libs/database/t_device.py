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
from typing import Optional, List

from aiou.mem import CachePool

from dimples import ID
from dimples.utils import SharedCacheManager
from dimples.database import DbInfo, DbTask

from .redis import DeviceCache
from .dos import DeviceStorage, DeviceInfo
from .dos.device import insert_device


class DevTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, identifier: ID,
                 cache_pool: CachePool, redis: DeviceCache, storage: DeviceStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._identifier = identifier
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> ID:
        return self._identifier

    # Override
    async def _load_redis_cache(self) -> Optional[List[DeviceInfo]]:
        devices = await self._redis.get_devices(identifier=self._identifier)
        if devices is None or len(devices) == 0:
            return None
        else:
            return devices

    # Override
    async def _save_redis_cache(self, value: List[DeviceInfo]) -> bool:
        return await self._redis.save_devices(devices=value, identifier=self._identifier)

    # Override
    async def _load_local_storage(self) -> Optional[List[DeviceInfo]]:
        devices = await self._dos.get_devices(identifier=self._identifier)
        if devices is None or len(devices) == 0:
            return None
        else:
            return devices

    # Override
    async def _save_local_storage(self, value: List[DeviceInfo]) -> bool:
        return await self._dos.save_devices(devices=value, identifier=self._identifier)


class DeviceTable:

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='devices')  # ID => DeviceInfo
        self._redis = DeviceCache(connector=info.redis_connector)
        self._dos = DeviceStorage(root=info.root_dir, public=info.public_dir, private=info.private_dir)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_task(self, identifier: ID) -> DevTask:
        return DevTask(identifier=identifier,
                       cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    async def get_devices(self, identifier: ID) -> Optional[List[DeviceInfo]]:
        task = self._new_task(identifier=identifier)
        return await task.load()

    async def save_devices(self, devices: List[DeviceInfo], identifier: ID) -> bool:
        task = self._new_task(identifier=identifier)
        return await task.save(value=devices)

    async def add_device(self, device: DeviceInfo, identifier: ID) -> bool:
        # get all devices info with ID
        array = await self.get_devices(identifier=identifier)
        if array is None:
            array = [device]
        else:
            array = insert_device(info=device, devices=array)
            if array is None:
                return False
        return await self.save_devices(devices=array, identifier=identifier)
