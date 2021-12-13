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
from typing import List, Optional

from dimp import json_encode, json_decode
from dimp import ID

from .base import Cache


def encode_address(address) -> bytes:
    return json_encode(o=address)


def decode_address(data: bytes) -> tuple:
    address = json_decode(data=data)
    assert isinstance(address, tuple), 'address error: %s' % data
    return address


class SessionCache(Cache):

    # session info cached in Redis will be removed after 5 hours.
    EXPIRES = 18000  # seconds

    @property  # Override
    def database(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def table(self) -> str:
        return 'session'

    """
        Session
        ~~~~~~~
        'address' - socket address

        redis key: 'mkm.session.{ID}.addresses'
        redis key: 'mkm.session.{address}.info'
    """
    def __addresses_key(self, identifier: ID) -> str:
        return '%s.%s.%s.addresses' % (self.database, self.table, identifier)

    def __info_key(self, address: tuple) -> str:
        return '%s.%s.%s.info' % (self.database, self.table, address)

    """
        ID -> socket address
    """

    def load_addresses(self, identifier: ID) -> List[tuple]:
        addr_key = self.__addresses_key(identifier=identifier)
        # 0. clear expired socket addresses (5 hours ago)
        expired = int(time.time()) - self.EXPIRES
        self.zremrangebyscore(name=addr_key, min_score=0, max_score=expired)
        # 1. get all socket addresses in the last 5 hours
        data = self.zrange(name=addr_key)
        if data is None:
            return []
        array = []
        for item in data:
            array.append(decode_address(data=item))
        return array

    def save_address(self, address: tuple, identifier: ID) -> bool:
        addr_key = self.__addresses_key(identifier=identifier)
        data = encode_address(address=address)
        now = int(time.time())
        return self.zadd(name=addr_key, mapping={data: now})

    def remove_address(self, address: tuple, identifier: ID) -> bool:
        addr_key = self.__addresses_key(identifier=identifier)
        data = encode_address(address=address)
        return self.zrem(addr_key, data)

    """
        socket address -> session info
    """

    def load_info(self, address: tuple) -> Optional[dict]:
        info_key = self.__info_key(address=address)
        data = self.get(name=info_key)
        if data is not None:
            return json_decode(data=data)

    def save_info(self, info: dict, address: tuple) -> bool:
        info_key = self.__info_key(address=address)
        data = json_encode(o=info)
        return self.set(name=info_key, value=data, expires=self.EXPIRES)

    def remove_info(self, address: tuple) -> bool:
        info_key = self.__info_key(address=address)
        return self.delete(info_key)

    def renew(self, address: tuple, identifier: ID = None) -> bool:
        info_key = self.__info_key(address=address)
        if self.exists(info_key):
            self.expire(name=info_key, ti=self.EXPIRES)
            if identifier is not None:
                self.save_address(identifier=identifier, address=address)
            return True
