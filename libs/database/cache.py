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
from threading import Thread
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

    def renewal(self, duration: int = 128):
        self.__expired = int(time.time()) + duration


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
    def purge(cls) -> int:
        """ Remove all expired cache holders """
        count = 0
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
                count += 1
        return count


class FrequencyChecker(Generic[K]):
    """ Frequency checker for duplicated queries """

    def __init__(self, expires: int = 3600):
        super().__init__()
        self.__expires = expires
        self.__map: Dict[K, int] = {}

    def expired(self, key: K, expires: int = None) -> bool:
        if expires is None:
            expires = self.__expires
        now = int(time.time())
        if now > self.__map.get(key, 0):
            self.__map[key] = now + expires
            return True


class CacheCleaner:

    def __init__(self):
        super().__init__()
        # running thread
        self.__thread: Optional[Thread] = None
        self.__running = False

    @property
    def running(self) -> bool:
        return self.__running

    def start(self):
        self.__force_stop()
        self.__running = True
        t = Thread(target=self.run)
        self.__thread = t
        t.start()

    def __force_stop(self):
        self.__running = False
        t: Thread = self.__thread
        if t is not None:
            # waiting 2 seconds for stopping the thread
            self.__thread = None
            t.join(timeout=5.0)

    def stop(self):
        self.__force_stop()

    def run(self):
        self.__running = True
        next_time = int(time.time()) + 300
        while self.running:
            # try to purge each 5 minutes
            now = int(time.time())
            if now < next_time:
                time.sleep(2)
                continue
            else:
                next_time = now + 300
            try:
                count = CachePool.purge()
                print('[DB] purge %d item(s) from cache pool' % count)
            except Exception as error:
                print('[DB] failed to purge cache: %s' % error)
