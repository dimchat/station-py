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
from typing import Optional, Tuple

from dimples import ID, ReliableMessage
from dimples import ResetCommand

from dimples.utils import CacheManager
from dimples.common import ResetGroupDBI
from dimples.common.dbi import is_expired

from .dos import ResetGroupStorage
from .redis import ResetGroupCache


class ResetGroupTable(ResetGroupDBI):
    """ Implementations of ResetGroupDBI """

    CACHE_EXPIRES = 300    # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = ResetGroupStorage(root=root, public=public, private=private)
        self.__redis = ResetGroupCache()
        man = CacheManager()
        self.__reset_cache = man.get_pool(name='group.reset')  # ID => (ResetCommand, ReliableMessage)

    def show_info(self):
        self.__dos.show_info()

    def _is_expired(self, group: ID, content: ResetCommand) -> bool:
        """ check old record with document time """
        new_time = content.time
        if new_time is None or new_time <= 0:
            return False
        # check old record
        old, _ = self.reset_command_message(group=group)
        if old is not None and is_expired(old_time=old.time, new_time=new_time):
            # command expired
            return False

    #
    #   Reset Group DBI
    #

    # Override
    def reset_command_message(self, group: ID) -> Tuple[Optional[ResetCommand], Optional[ReliableMessage]]:
        """ get reset command message for group """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__reset_cache.fetch(key=group, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__reset_cache.update(key=group, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return None, None
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            cmd, msg = self.__redis.load_reset(group=group)
            if msg is None and cmd is not None:
                # 3. check local storage
                cmd, msg = self.__dos.reset_command_message(group=group)
                # update redis server
                self.__redis.save_reset(group=group, content=cmd, msg=msg)
            value = (cmd, msg)
            # 3. update memory cache
            self.__reset_cache.update(key=group, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def save_reset_command_message(self, group: ID, content: ResetCommand, msg: ReliableMessage) -> bool:
        # 0. check command time
        if self._is_expired(group=group, content=content):
            # command expired, drop it
            return False
        # 1. store into memory cache
        self.__reset_cache.update(key=group, value=(content, msg), life_span=self.CACHE_EXPIRES)
        # 3. store into local storage
        return self.__dos.save_reset_command_message(group=group, content=content, msg=msg)
