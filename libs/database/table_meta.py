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

from typing import Optional, Dict

from dimp import ID, Meta

from .redis import MetaCache
from .dos import MetaStorage

from .cache import CacheHolder, CachePool


class MetaTable:

    def __init__(self):
        super().__init__()
        self.__redis = MetaCache()
        self.__dos = MetaStorage()
        # memory caches
        self.__caches: Dict[ID, CacheHolder[Meta]] = CachePool.get_caches('meta')

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        assert meta.match_identifier(identifier=identifier), 'meta invalid: %s, %s' % (identifier, meta)
        # 1. check memory cache
        holder = self.__caches.get(identifier)
        if holder is None or holder.value is None:
            # save to memory cache
            self.__caches[identifier] = CacheHolder(value=meta, life_span=36000)
        # 2. check redis server
        old = self.__redis.meta(identifier=identifier)
        if old is None:
            # save to redis server
            self.__redis.save_meta(meta=meta, identifier=identifier)
        # 3. check local storage
        old = self.meta(identifier=identifier)
        if old is None:
            # save to local storage
            return self.__dos.save_meta(meta=meta, identifier=identifier)
        # meta will not changed, we DO NOT need to update it here
        return True

    def meta(self, identifier: ID) -> Optional[Meta]:
        # 1. check memory cache
        holder = self.__caches.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__caches[identifier] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            info = self.__redis.meta(identifier=identifier)
            if info is None:
                # 3. check local storage
                info = self.__dos.meta(identifier=identifier)
                if info is not None:
                    # update redis server
                    self.__redis.save_meta(meta=info, identifier=identifier)
            # update memory cache
            holder = CacheHolder(value=info, life_span=36000)
            self.__caches[identifier] = holder
        # OK, return cached value
        return holder.value
