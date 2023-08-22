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
from typing import Optional, List

from dimples import ID

from dimples.utils import CacheManager
from dimples.common import ProviderDBI, StationDBI
from dimples.common import ProviderInfo, StationInfo

from .redis import StationCache
from .dos import StationStorage


class StationTable(ProviderDBI, StationDBI):
    """ Implementations of ProviderDBI, StationDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    # noinspection PyUnusedLocal
    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = StationStorage(root=root, public=public, private=private)
        self.__redis = StationCache()
        man = CacheManager()
        self.__isp_cache = man.get_pool(name='isp')            # 'providers' => List[ProviderInfo]
        self.__stations_cache = man.get_pool(name='stations')  # SP_ID => List[StationInfo

    # noinspection PyMethodMayBeStatic
    def show_info(self):
        self.__dos.show_info()

    #
    #   ProviderDBI
    #

    # Override
    def all_providers(self) -> List[ProviderInfo]:
        """ get list of (SP_ID, chosen) """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__isp_cache.fetch(key='providers', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__isp_cache.update(key='providers', life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return []
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.all_providers()
            if value is None or len(value) == 0:
                # 3. check local storage
                value = self.__dos.all_providers()
                if value is None or len(value) == 0:
                    value = [ProviderInfo(identifier=ProviderInfo.GSP, chosen=0)]
                # update redis server
                self.__redis.save_providers(providers=value)
            # update memory cache
            self.__isp_cache.update(key='providers', value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        self.__isp_cache.erase(key='providers')
        self.__redis.add_provider(identifier=identifier, chosen=chosen)
        self.__dos.add_provider(identifier=identifier, chosen=chosen)
        return True

    # Override
    def update_provider(self, identifier: ID, chosen: int) -> bool:
        self.__isp_cache.erase(key='providers')
        self.__redis.update_provider(identifier=identifier, chosen=chosen)
        self.__dos.update_provider(identifier=identifier, chosen=chosen)
        return True

    # Override
    def remove_provider(self, identifier: ID) -> bool:
        self.__isp_cache.erase(key='providers')
        self.__redis.remove_provider(identifier=identifier)
        self.__dos.remove_provider(identifier=identifier)
        return True

    #
    #   StationDBI
    #

    # Override
    def all_stations(self, provider: ID) -> List[StationInfo]:
        """ get list of (host, port, SP_ID, chosen) """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__stations_cache.fetch(key=provider, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__stations_cache.update(key=provider, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return []
                # neighbors expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.all_stations(provider=provider)
            if value is None or len(value) == 0:
                # 3. check local storage
                value = self.__dos.all_stations(provider=provider)
                if value is not None:
                    # update redis server
                    self.__redis.save_stations(stations=value, provider=provider)
            # update memory cache
            self.__stations_cache.update(key=provider, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    # Override
    def add_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = 0) -> bool:
        self.__stations_cache.erase(key=provider)
        self.__redis.add_station(identifier=identifier, host=host, port=port, provider=provider, chosen=chosen)
        self.__dos.add_station(identifier=identifier, host=host, port=port, provider=provider, chosen=chosen)
        return True

    # Override
    def update_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = None) -> bool:
        self.__stations_cache.erase(key=provider)
        self.__redis.update_station(identifier=identifier, host=host, port=port, provider=provider, chosen=chosen)
        self.__dos.update_station(identifier=identifier, host=host, port=port, provider=provider, chosen=chosen)
        return True

    # Override
    def remove_station(self, host: str, port: int, provider: ID) -> bool:
        self.__stations_cache.erase(key=provider)
        self.__redis.remove_station(host=host, port=port, provider=provider)
        self.__dos.remove_station(host=host, port=port, provider=provider)
        return True

    # Override
    def remove_stations(self, provider: ID) -> bool:
        self.__stations_cache.erase(key=provider)
        self.__redis.remove_stations(provider=provider)
        self.__dos.remove_stations(provider=provider)
        return True
