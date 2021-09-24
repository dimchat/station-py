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

from typing import Optional, List, Dict

from dimp import ID

from .redis import DeviceCache
from .dos import DeviceStorage

from .cache import CacheHolder, CachePool


class DeviceTable:

    def __init__(self):
        super().__init__()
        self.__redis = DeviceCache()
        self.__dos = DeviceStorage()
        # memory caches
        self.__caches: Dict[ID, CacheHolder[dict]] = CachePool.get_caches('device')

    def save_device(self, device: dict, identifier: ID) -> bool:
        # 1. update memory cache
        self.__caches[identifier] = CacheHolder(value=device)
        # 2. update redis server
        self.__redis.save_device(device=device, identifier=identifier)
        # 3. update local storage
        return self.__dos.save_device(device=device, identifier=identifier)

    def device(self, identifier: ID) -> Optional[dict]:
        # 1. check memory cache
        holder = self.__caches.get(identifier)
        if holder is not None and holder.alive:
            return holder.value
        else:  # place an empty holder to avoid frequent reading
            self.__caches[identifier] = CacheHolder(life_span=16)
        # 2. check redis server
        info = self.__redis.device(identifier=identifier)
        if info is not None:
            # update memory cache
            self.__caches[identifier] = CacheHolder(value=info)
            return info
        # 3. check local storage
        info = self.__dos.device(identifier=identifier)
        if info is not None:
            # update memory cache & redis server
            self.__caches[identifier] = CacheHolder(value=info)
            self.__redis.save_device(device=info, identifier=identifier)
            return info

    def save_device_token(self, token: str, identifier: ID) -> bool:
        # 1. update memory cache
        self.__caches.pop(identifier, None)
        # 2. update redis server
        self.__redis.save_device_token(token=token, identifier=identifier)
        # 3. update local storage
        return self.__dos.save_device_token(token=token, identifier=identifier)

    def device_tokens(self, identifier: ID) -> Optional[List[str]]:
        device = self.device(identifier=identifier)
        if device is not None:
            return device.get('tokens')
