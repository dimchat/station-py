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
from typing import Optional, Set, Tuple

from dimp import ID

from dimples.utils import CacheHolder, CacheManager
from dimples.common import ProviderDBI

from .dos.provider import insert_neighbor, remove_neighbor

from .redis import ProviderCache
from .dos import ProviderStorage


class ProviderTable(ProviderDBI):
    """ Implementations of ProviderDBI """

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = ProviderStorage(root=root, public=public, private=private)
        self.__redis = ProviderCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='isp')  # 'neighbors' => Set[Tuple[str, int, ID]]

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        self.__dos.show_info()

    def save_neighbors(self, stations: Set[Tuple[str, int, ID]]) -> bool:
        # 1. store into memory cache
        self.__cache.update(key='neighbors', value=stations, life_span=600)
        # 2. store into redis server
        self.__redis.save_neighbors(stations=stations)
        # 3. store into local storage
        return self.__dos.save_neighbors(stations=stations)

    #
    #   ProviderDBI
    #

    # Override
    def all_neighbors(self) -> Set[Tuple[str, int, Optional[ID]]]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key='neighbors', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # neighbors not load yet, wait to load
                self.__cache.update(key='neighbors', life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'neighbors cache error'
                if holder.is_alive(now=now):
                    # neighbors not exists
                    return set()
                # neighbors expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check redis server
            value = self.__redis.all_neighbors()
            if value is None:
                # 3. check local storage
                value = self.__dos.all_neighbors()
                if value is not None:
                    # update redis server
                    self.__redis.save_neighbors(stations=value)
            # update memory cache
            self.__cache.update(key='neighbors', value=value, life_span=600, now=now)
        # OK, return cached value
        return value

    # Override
    def get_neighbor(self, host: str, port: int) -> Optional[ID]:
        neighbors = self.all_neighbors()
        for station in neighbors:
            if host == station[0] and port == station[1]:
                return station[2]

    # Override
    def add_neighbor(self, host: str, port: int, identifier: ID = None) -> bool:
        neighbors = self.all_neighbors()
        if insert_neighbor(host=host, port=port, identifier=identifier, stations=neighbors):
            return self.save_neighbors(stations=neighbors)

    # Override
    def del_neighbor(self, host: str, port: int) -> Optional[ID]:
        neighbors = self.all_neighbors()
        ok, sid = remove_neighbor(host=host, port=port, stations=neighbors)
        if ok:
            self.save_neighbors(stations=neighbors)
        return sid
