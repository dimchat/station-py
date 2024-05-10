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

from typing import Optional, Tuple

from dimples import DateTime
from dimples import ID, ReliableMessage

from dimples.utils import CacheManager
from dimples.utils import is_before
from dimples import LoginDBI
from dimples import LoginCommand

from .redis import LoginCache
from .dos import LoginStorage


class LoginTable(LoginDBI):
    """ Implementations of LoginDBI """

    CACHE_EXPIRES = 300    # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = LoginStorage(root=root, public=public, private=private)
        self.__redis = LoginCache()
        man = CacheManager()
        self.__login_cache = man.get_pool(name='login')  # ID => (LoginCommand, ReliableMessage)

    def show_info(self):
        self.__dos.show_info()

    async def _is_expired(self, user: ID, content: LoginCommand) -> bool:
        """ check old record with command time """
        new_time = content.time
        if new_time is None or new_time <= 0:
            return False
        # check old record
        old, _ = await self.get_login_command_message(user=user)
        if old is not None and is_before(old_time=old.time, new_time=new_time):
            # command expired
            return True

    #
    #   Login DBI
    #

    # Override
    async def save_login_command_message(self, user: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        assert user == msg.sender, 'msg sender not match: %s => %s' % (user, msg.sender)
        assert user == content.identifier, 'cmd ID not match: %s => %s' % (user, content.identifier)
        # 0. check command time
        if await self._is_expired(user=user, content=content):
            # command expired, drop it
            return False
        value = (content, msg)
        # 1. store into memory cache
        self.__login_cache.update(key=user, value=value, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        await self.__redis.save_login(user=user, content=content, msg=msg)
        # 3. save into local storage
        return await self.__dos.save_login_command_message(user=user, content=content, msg=msg)

    # Override
    async def get_login_command_message(self, user: ID) -> Tuple[Optional[LoginCommand], Optional[ReliableMessage]]:
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__login_cache.fetch(key=user, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__login_cache.update(key=user, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return None, None
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            cmd, msg = await self.__redis.load_login(user=user)
            if msg is None:  # and cmd is not None:
                # cmd is a placeholder here
                # 3. check local storage
                cmd, msg = await self.__dos.get_login_command_message(user=user)
                # update redis server
                await self.__redis.save_login(user=user, content=cmd, msg=msg)
            value = (cmd, msg)
            # update memory cache
            self.__login_cache.update(key=user, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value
