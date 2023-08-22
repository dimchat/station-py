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
from typing import Optional, Dict

from dimples.utils import CacheManager
from dimples import ID
from dimples import GroupKeysDBI
from dimples.database import GroupKeysStorage

from .redis import GroupKeysCache


class GroupKeysTable(GroupKeysDBI):
    """ Implementations of GroupKeysDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = GroupKeysStorage(root=root, public=public, private=private)
        self.__redis = GroupKeysCache()
        man = CacheManager()
        self.__memory_cache = man.get_pool(name='group_keys')  # (ID, ID) => Dict

    def show_info(self):
        self.__dos.show_info()

    #
    #   CipherKey DBI
    #

    # Override
    def group_keys(self, group: ID, sender: ID) -> Optional[Dict[str, str]]:
        direction = (group, sender)
        now = time.time()
        # 1. check memory cache
        value, holder = self.__memory_cache.fetch(key=direction, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__memory_cache.update(key=direction, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return None
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.group_keys(group=group, sender=sender)
            if value is None:
                # 3. check local storage
                value = self.__dos.group_keys(group=group, sender=sender)
                if value is not None:
                    # update redis server
                    self.__redis.save_group_keys(group=group, sender=sender, keys=value)
            # update memory cache
            self.__memory_cache.update(key=direction, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def save_group_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> bool:
        identifier = (group, sender)
        # 0. check old record
        table = self.group_keys(group=group, sender=sender)
        if table is None or 'digest' not in table or 'digest' not in keys:
            # new keys
            table = keys
        elif table.get('digest') != keys.get('digest'):
            # key changed
            table = keys
        else:
            # same digest, merge keys
            for receiver in keys:
                table[receiver] = keys[receiver]
        # 1. store into memory cache
        self.__memory_cache.update(key=identifier, value=table, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_group_keys(group=group, sender=sender, keys=table)
        # 2. store into local storage
        return self.__dos.save_group_keys(group=group, sender=sender, keys=table)
