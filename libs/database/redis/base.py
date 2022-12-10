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

from typing import Optional, Dict, List, Tuple

from redis import Redis


g_db_0 = Redis(db=0)  # default
g_db_1 = Redis(db=1)  # mkm.meta
g_db_2 = Redis(db=2)  # mkm.document
g_db_3 = Redis(db=3)  # mkm.user
g_db_4 = Redis(db=4)  # mkm.group
g_db_7 = Redis(db=7)  # mkm.session
g_db_8 = Redis(db=8)  # dkd.msg
g_db_9 = Redis(db=9)  # dkd.key

g_dbs = {
    'mkm.meta': g_db_1,
    'mkm.document': g_db_2,
    'mkm.user': g_db_3,
    'mkm.group': g_db_4,
    'mkm.session': g_db_7,
    'dkd.msg': g_db_8,
    'dkd.key': g_db_9,
}


class Cache:

    @classmethod
    def get_redis(cls, db_name: Optional[str], tbl_name: str) -> Redis:
        if db_name is None:
            db = g_dbs.get(tbl_name)
        else:
            db = g_dbs.get('%s.%s' % (db_name, tbl_name))
            if db is None:
                db = g_dbs.get(tbl_name)
        if db is None:
            db = g_db_0
        return db

    @property
    def redis(self) -> Redis:
        return self.get_redis(db_name=self.db_name, tbl_name=self.tbl_name)

    @property
    def db_name(self) -> Optional[str]:
        """ database name for redis """
        raise NotImplemented

    @property
    def tbl_name(self) -> str:
        """ table name for redis """
        raise NotImplemented

    #
    #   Key -> Value
    #

    def set(self, name: str, value: bytes, expires: Optional[int] = None):
        """ Set value with name """
        self.redis.set(name=name, value=value, ex=expires)
        return True

    def get(self, name: str) -> Optional[bytes]:
        """ Get value with name """
        return self.redis.get(name=name)

    def exists(self, *names) -> bool:
        """ Check whether value exists with name """
        return self.redis.exists(*names)

    def delete(self, *names):
        """ Remove value with name """
        self.redis.delete(*names)
        return True

    def expire(self, name: str, ti: int) -> bool:
        """ Update expired time with name """
        self.redis.expire(name=name, time=ti)
        return True

    def scan(self, cursor: int, match: str, count: int) -> Tuple[int, Optional[List[bytes]]]:
        """ Scan key names, return next cursor and partial results """
        return self.redis.scan(cursor=cursor, match=match, count=count)

    #
    #   Hash Mapping
    #

    def hset(self, name: str, key: str, value: bytes):
        """ Set a value into a hash table with name & key """
        self.redis.hset(name=name, key=key, value=value)
        return True

    def hget(self, name: str, key: str) -> Optional[bytes]:
        """ Get value from the hash table with name & key """
        return self.redis.hget(name=name, key=key)

    def hgetall(self, name: str) -> Optional[Dict[bytes, bytes]]:
        """ Get all items from the hash table with name """
        return self.redis.hgetall(name=name)

    def hkeys(self, name: str) -> List[str]:
        """ Return the list of keys within hash name """
        return self.redis.hkeys(name=name)

    def hdel(self, name: str, key: str):
        """ Delete value from hash table with name & key """
        self.redis.hdel(name, key)
        return True

    #
    #   Hash Set
    #

    def sadd(self, name: str, *values):
        """ Add values into a hash set with name """
        self.redis.sadd(name, *values)
        return True

    def spop(self, name: str, count: Optional[int] = None):
        """ Remove and return a random member from the hash set with name """
        return self.redis.spop(name=name, count=count)

    def srem(self, name: str, *values):
        """ Remove values from the hash set with name """
        self.redis.srem(name, *values)
        return True

    def smembers(self, name: str) -> List[bytes]:
        """ Get all items of the hash set with name """
        return self.redis.smembers(name=name)

    #
    #   Ordered Set
    #

    def zadd(self, name: str, mapping: dict):
        """ Add value with score into an ordered set with name """
        self.redis.zadd(name=name, mapping=mapping)
        return True

    def zrem(self, name: str, *values):
        """ Remove values from the ordered set with name """
        self.redis.zrem(name, *values)
        return True

    def zremrangebyscore(self, name: str, min_score: int, max_score: int):
        """ Remove items with score range [min, max] """
        self.redis.zremrangebyscore(name=name, min=min_score, max=max_score)
        return True

    def zrange(self, name: str, start: int = 0, end: int = -1, desc: bool = False) -> List[bytes]:
        """ Get items with range [start, end] """
        return self.redis.zrange(name=name, start=start, end=end, desc=desc)

    def zcard(self, name: str) -> int:
        """ Get length of the ordered set with name """
        return self.redis.zcard(name=name)
