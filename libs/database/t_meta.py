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
from typing import Optional

from dimples import ID, Meta

from dimples.utils import CacheManager
from dimples.common import MetaDBI

from .redis import MetaCache
from .dos import MetaStorage


class MetaTable(MetaDBI):
    """ Implementations of MetaDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = MetaStorage(root=root, public=public, private=private)
        self.__redis = MetaCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='meta')  # ID => Meta

    def show_info(self):
        self.__dos.show_info()

    #
    #   Meta DBI
    #

    # Override
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        # 0. check old record
        old = self.meta(identifier=identifier)
        if old is not None:
            # meta exists, no need to update it
            return True
        # 1. store into memory cache
        self.__cache.update(key=identifier, value=meta, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_meta(meta=meta, identifier=identifier)
        # 3. store into local storage
        return self.__dos.save_meta(meta=meta, identifier=identifier)

    # Override
    def meta(self, identifier: ID) -> Optional[Meta]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # meta not load yet, wait to load
                self.__cache.update(key=identifier, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # meta not exists
                    return None
                # meta expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.meta(identifier=identifier)
            if value is None:
                # 3. check local storage
                value = self.__dos.meta(identifier=identifier)
                if value is not None:
                    # update redis server
                    self.__redis.save_meta(meta=value, identifier=identifier)
            # update memory cache
            self.__cache.update(key=identifier, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value
