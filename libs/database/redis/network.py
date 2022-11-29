# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
from typing import Optional, List

from dimsdk import utf8_encode, utf8_decode
from dimsdk import ID

from .base import Cache


class NetworkCache(Cache):

    @property  # Override
    def database(self) -> Optional[str]:
        return 'dim'

    @property  # Override
    def table(self) -> str:
        return 'network'

    """
        DIM Network
        ~~~~~~~~~~~

        redis key: 'dim.network.xxx'
    """
    def __key(self, suffix: str) -> str:
        return '%s.%s.%s' % (self.database, self.table, suffix)

    #
    #   Query Meta/Document
    #

    def add_meta_query(self, identifier: ID):
        key = self.__key(suffix='query-meta')
        value = utf8_encode(string=str(identifier))
        self.sadd(key, value)
        return True

    def pop_meta_query(self) -> Optional[ID]:
        name = self.__key(suffix='query-meta')
        value = self.spop(name=name)
        if value is not None:
            value = utf8_decode(data=value)
            return ID.parse(identifier=value)

    def add_document_query(self, identifier: ID):
        key = self.__key(suffix='query-document')
        value = utf8_encode(string=str(identifier))
        self.sadd(key, value)
        return True

    def pop_document_query(self) -> Optional[ID]:
        name = self.__key(suffix='query-document')
        value = self.spop(name=name)
        if value is not None:
            value = utf8_decode(data=value)
            return ID.parse(identifier=value)

    #
    #   Online Users
    #

    def add_online_user(self, station: ID, user: ID, last_time: int = None):
        key = self.__key(suffix=('%s.online-users' % station))
        if last_time is None or last_time == 0:
            last_time = int(time.time())
        value = utf8_encode(string=str(user))
        # add user ID with login time
        self.zadd(name=key, mapping={value: last_time})
        return True

    def remove_offline_users(self, station: ID, users: List[ID]):
        key = self.__key(suffix=('%s.online-users' % station))
        # 0. clear expired users (5 minutes ago)
        expired = int(time.time()) - 300
        self.zremrangebyscore(name=key, min_score=0, max_score=expired)
        # 1. clear offline users one by one
        for item in users:
            value = utf8_encode(string=str(item))
            self.zrem(key, value)
        return True

    def get_online_users(self, station: ID, start: int = 0, limit: int = -1) -> List[ID]:
        # 0. clear expired users
        self.remove_offline_users(station=station, users=[])
        # 1. get number of users
        key = self.__key(suffix=('%s.online-users' % station))
        count = self.zcard(name=key)
        if count <= start:
            return []
        if 0 < limit < (count - start):
            end = start + limit
        else:
            end = count
        # 2. get users with range [start, end)
        users = []
        values = self.zrange(name=key, start=start, end=(end - 1))
        for item in values:
            identifier = utf8_decode(data=item)
            identifier = ID.parse(identifier=identifier)
            if identifier is None:
                # should not happen
                continue
            users.append(identifier)
        return users
