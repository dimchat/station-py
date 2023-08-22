# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2023 Albert Moky
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

from dimples.utils import CacheManager
from dimples import ID, SymmetricKey
from dimples import PlainKey
from dimples import CipherKeyDBI

from .redis import CipherKeyCache


class CipherKeyTable(CipherKeyDBI):
    """ Implementations of CipherKeyDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__redis = CipherKeyCache()
        man = CacheManager()
        self.__memory_cache = man.get_pool(name='cipher')  # (ID, ID) => SymmetricKey

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!!      cipher key in memory only !!!')

    #
    #   CipherKey DBI
    #

    # Override
    def cipher_key(self, sender: ID, receiver: ID, generate: bool = False) -> Optional[SymmetricKey]:
        if receiver.is_broadcast:
            return plain_key
        now = time.time()
        direction = (sender, receiver)
        # 1. check memory cache
        value, holder = self.__memory_cache.fetch(key=direction, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to reload
                self.__memory_cache.update(key=direction, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now) and not generate:
                    # cache not exists
                    return None
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.cipher_key(sender=sender, receiver=receiver)
            if value is None and generate:
                # 3. generate and cache it
                value = SymmetricKey.generate(algorithm=SymmetricKey.AES)
                assert value is not None, 'failed to generate symmetric key'
                # update redis server
                self.__redis.save_cipher_key(key=value, sender=sender, receiver=receiver)
            # update memory cache
            self.__memory_cache.update(key=direction, value=value, life_span=self.CACHE_EXPIRES, now=now)
        return value

    # Override
    def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        if receiver.is_broadcast:
            # no need to store cipher key for broadcast message
            return False
        direction = (sender, receiver)
        # 1. store into memory cache
        self.__memory_cache.update(key=direction, value=key, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        return self.__redis.save_cipher_key(key=key, sender=sender, receiver=receiver)


plain_key = PlainKey()
