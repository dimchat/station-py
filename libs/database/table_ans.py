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

from typing import Optional, Set, Dict

from dimp import ID

from .redis import AddressNameCache
from .dos import AddressNameStorage

from .cache import CacheHolder, CachePool


class AddressNameTable:

    def __init__(self):
        super().__init__()
        self.__redis = AddressNameCache()
        self.__dos = AddressNameStorage()
        # memory caches
        self.__caches: Dict[str, CacheHolder[ID]] = CachePool.get_caches('ans')

    def save_record(self, name: str, identifier: ID) -> bool:
        # 1. update memory cache
        self.__caches[name] = CacheHolder(value=identifier)
        # 2. update redis server
        self.__redis.save_record(name=name, identifier=identifier)
        # 3. update local storage
        records = self.__dos.load_records()
        if name in records:
            return False
        records[name] = identifier
        return self.__dos.save_records(records=records)

    def record(self, name: str) -> Optional[ID]:
        # 1. check memory cache
        holder = self.__caches.get(name)
        if holder is not None and holder.alive:
            return holder.value
        else:  # place an empty holder to avoid frequent reading
            self.__caches[name] = CacheHolder(life_span=16)
        # 2. check redis server
        identifier = self.__redis.record(name=name)
        if identifier is not None:
            # update memory cache
            self.__caches[name] = CacheHolder(value=identifier)
            return identifier

    def names(self, identifier: ID) -> Set[str]:
        # TODO: cache to avoid frequent reading
        return self.__redis.names(identifier=identifier)
