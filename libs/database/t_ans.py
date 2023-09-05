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
from typing import Optional, Set, Dict

from dimples import ID

from dimples.utils import CacheManager

from .redis import AddressNameCache
from .dos import AddressNameStorage


class AddressNameTable:

    CACHE_EXPIRES = 300    # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = AddressNameStorage(root=root, public=public, private=private)
        self.__redis = AddressNameCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='ans')  # str => ID

    def show_info(self):
        self.__dos.show_info()

    def _load_records(self, now: float = None) -> Dict[str, ID]:
        # 1. check memory cache
        value, holder = self.__cache.fetch(key='all_records', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # ANS record not load yet, wait to load
                self.__cache.update(key='all_records', life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # ANS records not exists
                    return {}
                # ANS records expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. load from local storage
            value = self.__dos.load_records()
            self.__cache.update(key='all_records', value=value, life_span=300, now=now)
        return value

    def _save_records(self, records: Dict[str, ID], now: float = None) -> bool:
        self.__cache.update(key='all_records', value=records, life_span=300, now=now)
        return self.__dos.save_records(records=records)

    def save_record(self, name: str, identifier: ID) -> bool:
        now = time.time()
        # 1. update memory cache
        if identifier is not None:
            # remove: ID => Set[str]
            self.__cache.erase(key=identifier)
        # 2. update redis server
        self.__redis.save_record(name=name, identifier=identifier)
        # 3. update local storage
        all_records = self._load_records(now=now)
        all_records[name] = identifier
        return self._save_records(records=all_records, now=now)

    def record(self, name: str) -> Optional[ID]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=name, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # ANS record not load yet, wait to load
                self.__cache.update(key=name, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # ANS record not exists
                    return None
                # ANS record expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.record(name=name)
            if value is None:
                # 3. check local storage
                all_records = self._load_records(now=now)
                if all_records is not None:
                    # update redis server
                    value = all_records.get(name)
                    if value is not None:
                        self.__redis.save_record(name=name, identifier=value)
            # update memory cache
            self.__cache.update(key=name, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    def names(self, identifier: ID) -> Set[str]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # ANS record not load yet, wait to load
                self.__cache.update(key=identifier, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # ANS record not exists
                    return set()
                # ANS record expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.names(identifier=identifier)
            if value is None:
                # 3. check local storage
                all_records = self._load_records(now=now)
                if all_records is not None:
                    value = get_names(records=all_records, identifier=identifier)
            # update memory cache
            self.__cache.update(key=identifier, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value


def get_names(records: Dict[str, ID], identifier: ID) -> Set[str]:
    strings = set()
    for key in records:
        if identifier == records[key]:
            strings.add(key)
    return strings
