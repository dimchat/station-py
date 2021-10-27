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

from typing import Optional, List, Dict

from dimp import ID

from .redis import GroupCache
from .dos import GroupStorage

from .cache import CacheHolder, CachePool


class GroupTable:

    def __init__(self):
        super().__init__()
        self.__redis = GroupCache()
        self.__dos = GroupStorage()
        # memory caches
        self.__members: Dict[ID, CacheHolder[List[ID]]] = CachePool.get_caches(name='members')
        self.__keys_table: Dict[ID, CacheHolder[dict]] = CachePool.get_caches(name='encrypted-keys')

    def save_members(self, members: List[ID], group: ID) -> bool:
        # 1. save to memory cache
        self.__members[group] = CacheHolder(value=members)
        # 2. save to redis server
        self.__redis.save_members(members=members, group=group)
        # 3. save to local storage
        return self.__dos.save_members(members=members, group=group)

    def members(self, group: ID) -> List[ID]:
        # 1. check memory cache
        holder = self.__members.get(group)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__members[group] = CacheHolder(value=[], life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            array = self.__redis.members(group=group)
            if len(array) == 0:
                # 3. check local storage
                array = self.__dos.members(group=group)
                if len(array) > 0:
                    # update redis server
                    self.__redis.save_members(members=array, group=group)
            # update memory cache
            holder = CacheHolder(value=array)
            self.__members[group] = holder
        # OK, return cached value
        return holder.value

    def founder(self, group: ID) -> ID:
        # TODO: get founder
        pass

    def owner(self, group: ID) -> ID:
        # TODO: get owner
        pass

    def update_keys(self, keys: Dict[str, str], sender: ID, group: ID) -> bool:
        if keys is None:
            return False
        else:
            digest = keys.get('digest')
        # 0. check exists keys
        key_map = self.get_keys(sender=sender, group=group)
        if key_map is None or key_map.get('digest') is None:
            # no keys for this group+sender yet,
            # or keys without digest
            key_map = keys
            dirty = True
        elif digest is None or digest != key_map['digest']:
            # keys changed
            key_map = keys
            dirty = True
        else:
            # digests equal, update keys one by one
            dirty = False
            for (member, value) in keys.items():
                if value is None or len(value) == 0:
                    # should not happen
                    continue
                elif value == key_map.get(member):
                    # same value
                    continue
                key_map[member] = value
                dirty = True
        if not dirty:
            # nothing changed
            return True
        # 1. update memory cache
        table_holder = self.__keys_table.get(group)
        if table_holder is None:
            # place an empty holder to avoid frequent reading
            table_holder = CacheHolder(value={})
            self.__keys_table[group] = table_holder
        elif not table_holder.alive:
            # renewal the holder to avoid frequent reading
            table_holder.renewal(duration=3600)
        table: Dict[ID, CacheHolder[dict]] = table_holder.value
        table[sender] = CacheHolder(value=key_map)
        # 2. save to redis server
        self.__redis.save_keys(keys=key_map, sender=sender, group=group)
        # 3. save to local storage
        return self.__dos.save_keys(keys=key_map, sender=sender, group=group)

    def get_keys(self, sender: ID, group: ID) -> Optional[Dict[str, str]]:
        # get keys table from memory cache
        table_holder = self.__keys_table.get(group)
        if table_holder is None:
            # place an empty holder to avoid frequent reading
            table_holder = CacheHolder(value={}, life_span=128)
            self.__keys_table[group] = table_holder
        elif not table_holder.alive:
            # renewal the holder to avoid frequent reading
            table_holder.renewal()
        table: Dict[ID, CacheHolder[dict]] = table_holder.value
        # 1. check memory cache
        holder = table.get(sender)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                table[sender] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            keys = self.__redis.load_keys(sender=sender, group=group)
            if keys is None:
                # 3. check local storage
                keys = self.__dos.load_keys(sender=sender, group=group)
                if keys is not None:
                    # update redis server
                    self.__redis.save_keys(keys=keys, sender=sender, group=group)
            # update memory cache
            holder = CacheHolder(value=keys)
            table[sender] = holder
        # OK, return cached value
        table_holder.renewal(duration=36000)
        return holder.value

    def get_key(self, sender: ID, member: ID, group: ID) -> Optional[str]:
        keys = self.get_keys(sender=sender, group=group)
        if keys is not None:
            return keys.get(str(member))
