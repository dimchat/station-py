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
        self.__caches: Dict[str, CacheHolder[ID]] = CachePool.get_caches('ans.record')
        self.__names: Dict[ID, CacheHolder[Set[str]]] = CachePool.get_caches('ans.names')

    def save_record(self, name: str, identifier: ID) -> bool:
        # 1. update memory cache
        self.__caches[name] = CacheHolder(value=identifier)
        # 2. update redis server
        self.__redis.save_record(name=name, identifier=identifier)
        # 3. update local storage
        records = self.__dos.load_records()
        if identifier is None:
            records.pop(name, None)
        else:
            records[name] = identifier
        return self.__dos.save_records(records=records)

    def record(self, name: str) -> Optional[ID]:
        # 1. check memory cache
        holder = self.__caches.get(name)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__caches[name] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            identifier = self.__redis.record(name=name)
            # update memory cache
            holder = CacheHolder(value=identifier)
            self.__caches[name] = CacheHolder(value=identifier)
        # OK, return cached value
        return holder.value

    def names(self, identifier: ID) -> Set[str]:
        # 1. check memory cache
        holder = self.__names.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__names[identifier] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            aliases = self.__redis.names(identifier=identifier)
            # update memory cache
            holder = CacheHolder(value=aliases)
            self.__names[identifier] = holder
        # OK, return cached value
        return holder.value
