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

from typing import Optional, Dict, Tuple

from dimp import ID, SymmetricKey

from .redis import MessageKeyCache

from .cache import CacheHolder, CachePool


class MessageKeyTable:

    def __init__(self):
        super().__init__()
        self.__redis = MessageKeyCache()
        # memory caches
        self.__caches: Dict[Tuple[ID, ID], CacheHolder[SymmetricKey]] = CachePool.get_caches(name='msg_key')

    def cipher_key(self, sender: ID, receiver: ID) -> Optional[SymmetricKey]:
        # 1. check memory cache
        holder = self.__caches.get((sender, receiver))
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__caches[(sender, receiver)] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            msg_key = self.__redis.cipher_key(sender=sender, receiver=receiver)
            # update memory cache
            holder = CacheHolder(value=msg_key)
            self.__caches[(sender, receiver)] = holder
        # OK, return cached value
        return holder.value

    def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        # save to redis server
        if self.__redis.save_cipher_key(key=key, sender=sender, receiver=receiver):
            # clear cache to reload
            self.__caches.pop((sender, receiver), None)
            return True
