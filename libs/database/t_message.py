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
from typing import List, Tuple

from dimples import ID
from dimples import ReliableMessage

from dimples.utils import CacheHolder, CacheManager
from dimples.common import ReliableMessageDBI

from .redis import MessageCache


class PartialInfo:
    """ Partial messages with range [start, end] """

    def __init__(self, messages: List[ReliableMessage], remaining: int, start: int, limit: int):
        super().__init__()
        self.messages = messages
        self.remaining = remaining
        self.start = start
        self.limit = limit


class MessageTable(ReliableMessageDBI):
    """ Implementations of ReliableMessageDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__redis = MessageCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='message')  # ID => PartialInfo

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!! messages cached in memory only !!!')

    #
    #   ReliableMessageDBI
    #

    # Override
    def reliable_messages(self, receiver: ID, start: int = 0, limit: int = 1024) -> Tuple[List[ReliableMessage], int]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=receiver, now=now)
        if isinstance(value, PartialInfo):
            if value.start == start and value.limit == limit:
                # exactly!
                return value.messages, value.remaining
            # check range
            wanted_end = start + limit
            cached_end = value.start + value.limit
            if 0 <= value.start <= start and wanted_end <= cached_end:
                # within the range
                begin = start - value.start
                end = wanted_end - value.start
                remaining = value.remaining + cached_end - wanted_end
                return value.messages[begin:end], remaining
            # TODO: what about start < 0?
            value = None
        if value is None:
            # cache empty
            if holder is None:
                # messages not load yet, wait to load
                self.__cache.update(key=receiver, life_span=self.CACHE_REFRESHING, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'messages cache error'
                if holder.is_alive(now=now):
                    # messages not exists
                    return [], 0
                # messages expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            messages, remaining = self.__redis.reliable_messages(receiver=receiver, start=start, limit=limit)
            # 3. update memory cache
            value = PartialInfo(messages=messages, remaining=remaining, start=start, limit=limit)
            self.__cache.update(key=receiver, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value.messages, value.remaining

    # Override
    def save_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        # 1. store into redis server
        if self.__redis.save_reliable_message(msg=msg, receiver=receiver):
            # 2. clear cache to reload
            self.__cache.erase(key=receiver)
            return True

    # Override
    def remove_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        # 1. remove from redis server
        if self.__redis.remove_reliable_message(msg=msg, receiver=receiver):
            # 2. clear cache to reload
            self.__cache.erase(key=receiver)
            return True
