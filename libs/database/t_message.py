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
from typing import List

from dimp import ID
from dimp import ReliableMessage

from dimples.utils import CacheHolder, CacheManager
from dimples.common import ReliableMessageDBI

from .redis import MessageCache


class MessageTable(ReliableMessageDBI):
    """ Implementations of ReliableMessageDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__redis = MessageCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='message')  # ID => List[ReliableMessage]

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        print('!!! messages cached in memory only !!!')

    #
    #   ReliableMessageDBI
    #

    # Override
    def reliable_messages(self, receiver: ID) -> List[ReliableMessage]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=receiver, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # messages not load yet, wait to load
                self.__cache.update(key=receiver, life_span=8, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'messages cache error'
                if holder.is_alive(now=now):
                    # messages not exists
                    return []
                # messages expired, wait to reload
                holder.renewal(duration=8, now=now)
            # 2. check redis server
            value = self.__redis.reliable_messages(receiver=receiver)
            # 3. update memory cache
            if len(value) < MessageCache.LIMIT:
                self.__cache.update(key=receiver, value=value, life_span=8, now=now)
            else:
                # maybe part of stored messages, reload seconds later
                self.__cache.update(key=receiver, value=value, life_span=3, now=now)
        # OK, return cached value
        return value

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
