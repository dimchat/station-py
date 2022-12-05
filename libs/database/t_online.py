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
from typing import Set, Tuple

from dimples import ID

from dimples.utils import CacheHolder, CacheManager
from dimples.database import OnlineTable as SuperTable

from .redis import LoginCache


class OnlineTable(SuperTable):
    """ Implementations of OnlineDBI """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__(root=root, public=public, private=private)
        self.__redis = LoginCache()
        man = CacheManager()
        self.__online_cache = man.get_pool(name='session.online')  # 'active_users' => Set(ID)

    #
    #   Online DBI
    #

    # Override
    def active_users(self) -> Set[ID]:
        """ read by archivist bot """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__online_cache.fetch(key='active_users', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # active_users not load yet, wait to load
                self.__online_cache.update(key='active_users', life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'active_users cache error'
                if holder.is_alive(now=now):
                    # active_users not exists
                    return set()
                # active_users expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check redis server
            value = self.__redis.active_users()
            if len(value) == 0:
                # 3. check local cache
                value = super().active_users()
            # update memory cache
            self.__online_cache.update(key='active_users', value=value, life_span=300, now=now)
        # OK, return cached value
        return value

    # # Override
    # def socket_addresses(self, identifier: ID) -> Set[Tuple[str, int]]:
    #     """ read by archivist bot """
    #     now = time.time()
    #     # 1. check memory cache
    #     value, holder = self.__online_cache.fetch(key=identifier, now=now)
    #     if value is None:
    #         # cache empty
    #         if holder is None:
    #             # sockets not load yet, wait to load
    #             self.__online_cache.update(key=identifier, life_span=128, now=now)
    #         else:
    #             assert isinstance(holder, CacheHolder), 'socket address cache error'
    #             if holder.is_alive(now=now):
    #                 # socket not exists
    #                 return set()
    #             # socket expired, wait to reload
    #             holder.renewal(duration=128, now=now)
    #         # 2. check redis server
    #         value = self.__redis.socket_addresses(identifier=identifier)
    #         if len(value) == 0:
    #             # 3. check local cache
    #             value = super().socket_addresses(identifier=identifier)
    #         # update memory cache
    #         self.__online_cache.update(key=identifier, value=value, life_span=300, now=now)
    #     # OK, return cached value
    #     return value

    # Override
    def add_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        """ wrote by station only """
        # 1. store into local cache
        sockets = super().add_socket_address(identifier=identifier, address=address)
        # # 2. store into local cache
        # self.__online_cache.update(key=identifier, value=sockets, life_span=300)
        # 3. refresh Redis Server
        self.__redis.save_socket_addresses(identifier=identifier, addresses=sockets)
        return sockets

    # Override
    def remove_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        """ wrote by station only """
        # 1. remove from local cache
        sockets = super().remove_socket_address(identifier=identifier, address=address)
        # # 2. store into local cache
        # self.__online_cache.update(key=identifier, value=sockets, life_span=300)
        # 3. refresh Redis Server
        self.__redis.save_socket_addresses(identifier=identifier, addresses=sockets)
        return sockets
