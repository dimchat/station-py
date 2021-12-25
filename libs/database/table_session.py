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

from typing import List, Dict, Optional, Set

from dimp import ID
from dimp import hex_encode
from dimsdk.plugins.aes import random_bytes

from .redis import SessionCache

from .cache import CacheHolder, CachePool


def generate_session_key() -> str:
    return hex_encode(data=random_bytes(32))


class SessionTable:

    def __init__(self):
        super().__init__()
        self.__redis = SessionCache()
        # memory caches
        self.__session_addresses: Dict[ID, CacheHolder[List[tuple]]] = CachePool.get_caches(name='session.addresses')
        self.__session_table: Dict[tuple, CacheHolder[dict]] = CachePool.get_caches(name='session.info')

    def _get_addresses(self, identifier: ID) -> List[tuple]:
        # 1. check memory cache
        holder = self.__session_addresses.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__session_addresses[identifier] = CacheHolder(value=[], life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            array = self.__redis.load_addresses(identifier=identifier)
            holder = CacheHolder(value=array)
            # update memory cache
            self.__session_addresses[identifier] = holder
        # OK, return cache value
        return holder.value

    def _save_address(self, address: tuple, identifier: ID) -> bool:
        # save to redis server
        if self.__redis.save_address(address=address, identifier=identifier):
            # clear cache to reload
            self.__session_addresses.pop(identifier, None)
            return True

    def _remove_address(self, address: tuple, identifier: ID) -> bool:
        # remove from redis server
        if self.__redis.remove_address(address=address, identifier=identifier):
            # clear cache to reload
            self.__session_addresses.pop(identifier, None)
            return True

    def _get_info(self, address: tuple) -> Optional[dict]:
        # 1. check memory cache
        holder = self.__session_table.get(address)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__session_table[address] = CacheHolder(value={}, life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            info = self.__redis.load_info(address=address)
            holder = CacheHolder(value=info)
            # update memory cache
            self.__session_table[address] = holder
        # OK, return cache value
        return holder.value

    def _save_info(self, info: dict, address: tuple) -> bool:
        # save to redis server
        if self.__redis.save_info(info=info, address=address):
            # clear cache to reload
            self.__session_table.pop(address, None)
            return True

    def _remove_info(self, address: tuple) -> bool:
        # remove from redis server
        if self.__redis.remove_info(address=address):
            # clear cache to reload
            self.__session_table.pop(address, None)
            return True

    def active_sessions(self, identifier: ID) -> Set[dict]:
        """ Get all active sessions """
        address = self._get_addresses(identifier=identifier)
        if address is None:
            return set()
        sessions = set()
        for addr in address:
            info = self._get_info(address=addr)
            if info is None:
                # session expired?
                continue
            sessions.add(info)
        return sessions

    def fetch_session(self, address: tuple) -> dict:
        """ Get/create session info """
        info = self._get_info(address=address)
        if info is None:  # or info.get('key') is None:
            info = {
                'address': address,
                'key': generate_session_key(),
            }
            self._save_info(info=info, address=address)
        return info

    def update_session(self, address: tuple, identifier: ID) -> bool:
        """ Update user ID with address """
        info = self._get_info(address=address)
        if info is None:
            return False
        info['ID'] = str(identifier)
        if self._save_info(info=info, address=address):
            return self._save_address(address=address, identifier=identifier)
