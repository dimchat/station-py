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

from .dos import GroupKeysStorage
from .redis import GroupKeysCache


class GroupKeysTable(GroupKeysDBI):
    """ Implementations of GroupKeysDBI """

    CACHE_EXPIRES = 300    # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = GroupKeysStorage(root=root, public=public, private=private)
        self.__redis = GroupKeysCache()
        man = CacheManager()
        self.__keys_cache = man.get_pool(name='group.keys')   # (sender, group) => Dict[str, str]

    def show_info(self):
        self.__dos.show_info()

    def _merge_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> Dict[str, str]:
        if 'digest' not in keys:
            # FIXME: old version?
            return keys
        # 0. check old record
        table = self.group_keys(group=group, sender=sender)
        if table is None or 'digest' not in table:
            # new keys
            return keys
        elif table.get('digest') != keys.get('digest'):
            # key changed
            return keys
        else:
            # same digest, merge keys
            table = table.copy()
            for receiver in keys:
                table[receiver] = keys[receiver]
            return table

    #
    #   Group Keys DBI
    #

    # Override
    def group_keys(self, group: ID, sender: ID) -> Optional[Dict[str, str]]:
        now = time.time()
        identifier = (group, sender)
        # 1. check memory cache
        value, holder = self.__keys_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__keys_cache.update(key=identifier, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return {}
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.group_keys(group=group, sender=sender)
            if value is None:
                # 3. check local storage
                value = self.__dos.group_keys(group=group, sender=sender)
                if value is None:
                    value = {}  # placeholder
                # update redis server
                self.__redis.save_group_keys(keys=value, sender=sender, group=group)
            # update memory cache
            self.__keys_cache.update(key=identifier, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def save_group_keys(self, group: ID, sender: ID, keys: Dict[str, str]) -> bool:
        identifier = (group, sender)
        # 0. check old record
        keys = self._merge_keys(group=group, sender=sender, keys=keys)
        # 1. store into memory cache
        self.__keys_cache.update(key=identifier, value=keys, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_group_keys(keys=keys, sender=sender, group=group)
        # 3. store into local storage
        return self.__dos.save_group_keys(keys=keys, sender=sender, group=group)
