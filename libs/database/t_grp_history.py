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

from typing import Optional, Tuple, List

from dimples import DateTime
from dimples import ID, ReliableMessage
from dimples import GroupCommand, ResetCommand, ResignCommand

from dimples.utils import CacheManager
from dimples.common import GroupHistoryDBI

from .dos import GroupHistoryStorage
from .redis import GroupHistoryCache


class GroupHistoryTable(GroupHistoryDBI):
    """ Implementations of GroupHistoryDBI """

    CACHE_EXPIRES = 300    # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = GroupHistoryStorage(root=root, public=public, private=private)
        self.__redis = GroupHistoryCache()
        man = CacheManager()
        self.__history_cache = man.get_pool(name='group.history')  # ID => List

    def show_info(self):
        self.__dos.show_info()

    async def save_group_histories(self, group: ID, histories: List[Tuple[GroupCommand, ReliableMessage]]) -> bool:
        # 1. store into memory cache
        self.__history_cache.update(key=group, value=histories, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        await self.__redis.save_group_histories(group=group, histories=histories)
        # 3. store into local storage
        return await self.__dos.save_group_histories(group=group, histories=histories)

    #
    #   Group History DBI
    #

    # Override
    async def save_group_history(self, group: ID, content: GroupCommand, message: ReliableMessage) -> bool:
        histories = await self.get_group_histories(group=group)
        item = (content, message)
        histories.append(item)
        return await self.save_group_histories(group=group, histories=histories)

    # Override
    async def get_group_histories(self, group: ID) -> List[Tuple[GroupCommand, ReliableMessage]]:
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__history_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__history_cache.update(key=group, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # data not found
                    return []
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = await self.__redis.load_group_histories(group=group)
            if value is None:
                # 3. check local storage
                value = await self.__dos.load_group_histories(group=group)
                if value is None:
                    value = []  # placeholder
                # update redis server
                await self.__redis.save_group_histories(group=group, histories=value)
            # update memory cache
            self.__history_cache.update(key=group, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    async def get_reset_command_message(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        histories = await self.get_group_histories(group=group)
        pos = len(histories)
        while pos > 0:
            pos -= 1
            his = histories[pos]
            cmd = his[0]
            msg = his[1]
            if isinstance(cmd, ResetCommand):
                return cmd, msg
        return None, None

    # Override
    async def clear_group_member_histories(self, group: ID) -> bool:
        histories = await self.get_group_histories(group=group)
        if len(histories) == 0:
            # history empty
            return True
        array = []
        removed = 0
        for his in histories:
            if isinstance(his[0], ResignCommand):
                # keep 'resign' command messages
                array.append(his)
            else:
                # remove other command messages
                removed += 1
        # if nothing changed, return True
        # else, save new histories
        return removed == 0 or await self.save_group_histories(group=group, histories=array)

    # Override
    async def clear_group_admin_histories(self, group: ID) -> bool:
        histories = await self.get_group_histories(group=group)
        if len(histories) == 0:
            # history empty
            return True
        array = []
        removed = 0
        for his in histories:
            if isinstance(his[0], ResignCommand):
                # remove 'resign' command messages
                removed += 1
            else:
                # keep other command messages
                array.append(his)
        # if nothing changed, return True
        # else, save new histories
        return removed == 0 or await self.save_group_histories(group=group, histories=array)
