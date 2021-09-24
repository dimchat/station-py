# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

"""
    Database module
    ~~~~~~~~~~~~~~~

"""

import time
from typing import TypeVar, Generic, Optional, Dict, Set

K = TypeVar('K')
V = TypeVar('V')


class CacheHolder(Generic[V]):

    def __init__(self, value: Optional[V] = None, life_span: int = 3600):
        super().__init__()
        self.__value = value
        self.__expired = int(time.time()) + life_span

    @property
    def value(self) -> V:
        return self.__value

    @property
    def alive(self) -> bool:
        return int(time.time()) < self.__expired


class CachePool(Generic[K, V]):

    shared_pool: Dict[str, Dict[K, CacheHolder[V]]] = {}  # global cache pool

    @classmethod
    def get_caches(cls, name: str) -> Dict[K, CacheHolder[V]]:
        """ Get caches for holders """
        caches = cls.shared_pool.get(name)
        if caches is None:
            caches = {}
            cls.shared_pool[name] = caches
        return caches

    @classmethod
    def purge(cls):
        """ Remove all expired cache holders """
        tables = cls.shared_pool.keys()
        for name in tables:
            caches = cls.shared_pool.get(name)
            if caches is None:
                continue
            expired: Set = set()
            for key, holder in caches.items():
                if holder is not None and not holder.alive:
                    expired.add(key)
            # remove expired holders
            for key in expired:
                caches.pop(key, None)
