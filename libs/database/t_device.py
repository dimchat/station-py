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

from .redis import DeviceCache
from .dos import DeviceStorage


class DeviceTable:

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = DeviceStorage(root=root, public=public, private=private)
        self.__redis = DeviceCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='device')  # ID => dict

    def show_info(self):
        self.__dos.show_info()

    def save_device(self, device: dict, identifier: ID) -> bool:
        # 1. store into memory cache
        self.__cache.update(key=identifier, value=device, life_span=60)
        # 2. store into redis server
        self.__redis.save_device(device=device, identifier=identifier)
        # 3. store into local storage
        return self.__dos.save_device(device=device, identifier=identifier)

    def device(self, identifier: ID) -> Optional[dict]:
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
                    return None
                # meta expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.device(identifier=identifier)
            if value is None:
                # 3. check local storage
                value = self.__dos.device(identifier=identifier)
                if value is not None:
                    # update redis server
                    self.__redis.save_device(device=value, identifier=identifier)
            # update memory cache
            self.__cache.update(key=identifier, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    def save_device_token(self, token: str, identifier: ID) -> bool:
        # 1. remove: ID => dict
        self.__cache.erase(key=identifier)
        # 2. update redis server
        self.__redis.save_device_token(token=token, identifier=identifier)
        # 3. update local storage
        return self.__dos.save_device_token(token=token, identifier=identifier)

    def device_tokens(self, identifier: ID) -> Optional[List[str]]:
        device = self.device(identifier=identifier)
        if device is not None:
            return device.get('tokens')
