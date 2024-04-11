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

from ...utils import Logging


class RedisConnector(Logging):

    def __init__(self):
        super().__init__()
        # config
        self.__host = 'localhost'
        self.__port = 6379
        self.__password = None
        self.__enable = False
        # databases
        self.__dbs = {
            # 0 - default
            # 1 - mkm.meta
            # 2 - mkm.document
            # 3 - mkm.user
            # 4 - mkm.group
            # 5
            # 6
            # 7 - mkm.session
            # 8 - dkd.msg
            # 9 - dkd.key
        }

    def get_redis(self, name: str) -> Optional[Redis]:
        if name == 'default':
            return self.redis(order=0)
        #
        #  MingKeMing
        #
        elif name == 'mkm.meta':
            return self.redis(order=1)
        elif name == 'mkm.document':
            return self.redis(order=2)
        elif name == 'mkm.user':
            return self.redis(order=3)
        elif name == 'mkm.group':
            return self.redis(order=4)
        #
        #  Session
        #
        elif name == 'mkm.session':
            return self.redis(order=7)
        #
        #  DaoKeDao
        #
        elif name == 'dkd.msg':
            return self.redis(order=8)
        elif name == 'dkd.key':
            return self.redis(order=9)

    def redis(self, order: int) -> Optional[Redis]:
        if self.__enable:
            db = self.__dbs.get(order)
            if db is None:
                host = self.__host
                port = self.__port
                password = self.__password
                self.info(msg='create redis db: %d (%s:%d) pwd: "%s"' % (order, host, port, password))
                db = Redis(db=order, host=host, port=port, password=password)
                self.__dbs[order] = db
            return db

    def set_host(self, ip: str):
        self.__host = ip

    def set_port(self, n: int):
        self.__port = n

    def set_password(self, pwd: str):
        self.__password = pwd

    def set_enable(self, flag: bool):
        self.__enable = flag


# shared connector
g_dbc = RedisConnector()


class Cache:

    #
    #   Config
    #

    @classmethod
    def set_redis_host(cls, host: str):
        g_dbc.set_host(host)

    @classmethod
    def set_redis_port(cls, port: int):
        g_dbc.set_port(port)

    @classmethod
    def set_redis_password(cls, password: str):
        g_dbc.set_password(password)

    @classmethod
    def set_redis_enable(cls, enable: bool):
        g_dbc.set_enable(enable)

    #
    #   Connect
    #

    @classmethod
    def get_redis(cls, db_name: Optional[str], tbl_name: str) -> Optional[Redis]:
        if db_name is None:
            db = g_dbc.get_redis(name=tbl_name)
        else:
            db = g_dbc.get_redis(name='%s.%s' % (db_name, tbl_name))
            if db is None:
                db = g_dbc.get_redis(name=tbl_name)
        if db is None:
            db = g_dbc.redis(order=0)
        return db

    @property
    def redis(self) -> Optional[Redis]:
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
        redis = self.redis
        if redis is not None:
            redis.set(name=name, value=value, ex=expires)
        return True

    def get(self, name: str) -> Optional[bytes]:
        """ Get value with name """
        redis = self.redis
        if redis is not None:
            return redis.get(name=name)

    def exists(self, *names) -> bool:
        """ Check whether value exists with name """
        redis = self.redis
        if redis is not None:
            return redis.exists(*names)

    def delete(self, *names):
        """ Remove value with name """
        redis = self.redis
        if redis is not None:
            redis.delete(*names)
        return True

    def expire(self, name: str, ti: int) -> bool:
        """ Update expired time with name """
        redis = self.redis
        if redis is not None:
            redis.expire(name=name, time=ti)
        return True

    def scan(self, cursor: int, match: str, count: int) -> Tuple[int, Optional[List[bytes]]]:
        """ Scan key names, return next cursor and partial results """
        redis = self.redis
        if redis is not None:
            return redis.scan(cursor=cursor, match=match, count=count)
        return 0, None

    #
    #   Hash Mapping
    #

    def hset(self, name: str, key: str, value: bytes):
        """ Set a value into a hash table with name & key """
        redis = self.redis
        if redis is not None:
            redis.hset(name=name, key=key, value=value)
        return True

    def hget(self, name: str, key: str) -> Optional[bytes]:
        """ Get value from the hash table with name & key """
        redis = self.redis
        if redis is not None:
            return redis.hget(name=name, key=key)

    def hgetall(self, name: str) -> Optional[Dict[bytes, bytes]]:
        """ Get all items from the hash table with name """
        redis = self.redis
        if redis is not None:
            return redis.hgetall(name=name)

    def hkeys(self, name: str) -> List[str]:
        """ Return the list of keys within hash name """
        redis = self.redis
        if redis is not None:
            return redis.hkeys(name=name)
        return []

    def hdel(self, name: str, key: str):
        """ Delete value from hash table with name & key """
        redis = self.redis
        if redis is not None:
            redis.hdel(name, key)
        return True

    #
    #   Hash Set
    #

    def sadd(self, name: str, *values):
        """ Add values into a hash set with name """
        redis = self.redis
        if redis is not None:
            redis.sadd(name, *values)
        return True

    def spop(self, name: str, count: Optional[int] = None):
        """ Remove and return a random member from the hash set with name """
        redis = self.redis
        if redis is not None:
            return redis.spop(name=name, count=count)

    def srem(self, name: str, *values):
        """ Remove values from the hash set with name """
        redis = self.redis
        if redis is not None:
            redis.srem(name, *values)
        return True

    def smembers(self, name: str) -> List[bytes]:
        """ Get all items of the hash set with name """
        redis = self.redis
        if redis is not None:
            return redis.smembers(name=name)
        return []

    #
    #   Ordered Set
    #

    def zadd(self, name: str, mapping: dict):
        """ Add value with score into an ordered set with name """
        redis = self.redis
        if redis is not None:
            redis.zadd(name=name, mapping=mapping)
        return True

    def zrem(self, name: str, *values):
        """ Remove values from the ordered set with name """
        redis = self.redis
        if redis is not None:
            redis.zrem(name, *values)
        return True

    def zremrangebyscore(self, name: str, min_score: int, max_score: int):
        """ Remove items with score range [min, max] """
        redis = self.redis
        if redis is not None:
            redis.zremrangebyscore(name=name, min=min_score, max=max_score)
        return True

    def zrange(self, name: str, start: int = 0, end: int = -1, desc: bool = False) -> List[bytes]:
        """ Get items with range [start, end] """
        redis = self.redis
        if redis is not None:
            return redis.zrange(name=name, start=start, end=end, desc=desc)
        return []

    def zcard(self, name: str) -> int:
        """ Get length of the ordered set with name """
        redis = self.redis
        if redis is not None:
            return redis.zcard(name=name)
        return 0
