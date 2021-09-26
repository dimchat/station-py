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

from typing import List, Dict

from dimp import ID
from dimp import ReliableMessage

from .redis import MessageCache

from .cache import CacheHolder, CachePool


class MessageTable:

    def __init__(self):
        super().__init__()
        self.__redis = MessageCache()
        # memory caches
        self.__caches: Dict[ID, CacheHolder[List[ReliableMessage]]] = CachePool.get_caches('messages')

    def save_message(self, msg: ReliableMessage) -> bool:
        # save to redis server
        if self.__redis.save_message(msg=msg):
            # clear cache to reload
            receiver = msg.receiver
            self.__caches.pop(receiver, None)
            return True

    def remove_message(self, msg: ReliableMessage) -> bool:
        # remove from redis server
        if self.__redis.remove_message(msg=msg):
            # clear cache to reload
            receiver = msg.receiver
            self.__caches.pop(receiver, None)
            return True

    def messages(self, receiver: ID) -> List[ReliableMessage]:
        # 1. check memory cache
        holder = self.__caches.get(receiver)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__caches[receiver] = CacheHolder(value=[], life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            array = self.__redis.messages(receiver=receiver)
            # update memory cache
            holder = CacheHolder(value=array)
            self.__caches[receiver] = holder
        # OK, return cached value
        return holder.value
