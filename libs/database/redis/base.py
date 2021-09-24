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

from typing import Optional, Dict, List

from redis import Redis


g_db_0 = Redis(db=0)  # default
g_db_1 = Redis(db=1)  # mkm.meta
g_db_2 = Redis(db=2)  # mkm.document
g_db_3 = Redis(db=3)  # mkm.user
g_db_4 = Redis(db=4)  # mkm.group
g_db_8 = Redis(db=8)  # dkd.msg

g_dbs = {
    'mkm.meta': g_db_1,
    'mkm.document': g_db_2,
    'mkm.user': g_db_3,
    'mkm.group': g_db_4,
    'dkd.msg': g_db_8,
}


class Cache:

    @classmethod
    def get_redis(cls, table: str, database: Optional[str] = None) -> Redis:
        if database is None:
            db = g_dbs.get(table)
        else:
            db = g_dbs.get('%s.%s' % (database, table))
            if db is None:
                db = g_dbs.get(table)
        if db is None:
            db = g_db_0
        return db

    @property
    def redis(self) -> Redis:
        return self.get_redis(table=self.table, database=self.database)

    @property
    def database(self) -> Optional[str]:
        raise NotImplemented

    @property
    def table(self) -> str:
        raise NotImplemented

    #
    #   Key -> Value
    #

    def set(self, name: str, value: bytes, expires: Optional[int] = None):
        """ Set value with name """
        self.redis.set(name=name, value=value, ex=expires)

    def get(self, name: str) -> Optional[bytes]:
        """ Get value with name """
        return self.redis.get(name=name)

    def exists(self, *names) -> bool:
        """ Check whether value exists with name """
        return self.redis.exists(*names)

    def delete(self, *names):
        """ Remove value with name """
        self.redis.delete(*names)

    #
    #   Hash Mapping
    #

    def hset(self, name: str, key: str, value: bytes):
        """ Set a value into a hash table with name & key """
        self.redis.hset(name=name, key=key, value=value)

    def hget(self, name: str, key: str) -> Optional[bytes]:
        """ Get value from the hash table with name & key """
        return self.redis.hget(name=name, key=key)

    def hgetall(self, name: str) -> Optional[Dict[str, bytes]]:
        """ Get all items from the hash table with name """
        return self.redis.hgetall(name=name)

    #
    #   Hash Set
    #

    def sadd(self, name: str, *values):
        """ Add values into a hash set with name """
        self.redis.sadd(name, *values)

    def srem(self, name: str, *values):
        """ Remove values from the hash set with name """
        self.redis.srem(name, *values)

    def smembers(self, name: str) -> List[bytes]:
        """ Get all items of the hash set with name """
        return self.redis.smembers(name=name)

    #
    #   Ordered Set
    #

    def zadd(self, name: str, mapping: dict):
        """ Add value with score into an ordered set with name """
        self.redis.zadd(name=name, mapping=mapping)

    def zrem(self, name: str, *values):
        """ Remove values from the ordered set with name """
        self.redis.zrem(name, *values)

    def zremrangebyscore(self, name: str, min_score: int, max_score: int):
        """ Remove items with score range [min, max] """
        self.redis.zremrangebyscore(name=name, min=min_score, max=max_score)

    def zscan(self, name: str) -> List[bytes]:
        """ Get all item (ordered by scores) """
        values = []
        res = self.redis.zscan(name=name)
        for item in res[1]:
            values.append(item[0])
        return values

    def zrange(self, name: str, start: int = 0, end: int = -1, desc: bool = False) -> List[bytes]:
        """ Get items with range [start, end] """
        return self.redis.zrange(name=name, start=start, end=end, desc=desc)

    def zcard(self, name: str) -> int:
        """ Get length of the ordered set with name """
        return self.redis.zcard(name=name)
