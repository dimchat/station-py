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
from typing import Optional, Tuple

from dimples import ID, ReliableMessage

from dimples.utils import CacheManager
from dimples.common import LoginDBI
from dimples.common import LoginCommand
from dimples.common.dbi import is_expired

from .redis import LoginCache
from .dos import LoginStorage


class LoginTable(LoginDBI):
    """ Implementations of LoginDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = LoginStorage(root=root, public=public, private=private)
        self.__redis = LoginCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='login')  # ID => (LoginCommand, ReliableMessage)

    def show_info(self):
        self.__dos.show_info()

    #
    #   Login DBI
    #

    # Override
    def save_login_command_message(self, user: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        assert user == msg.sender, 'msg sender not match: %s => %s' % (user, msg.sender)
        assert user == content.identifier, 'cmd ID not match: %s => %s' % (user, content.identifier)
        # 0. check old record with time
        old, _ = self.login_command_message(user=user)
        if old is not None and is_expired(old_time=old.time, new_time=content.time):
            # command expired, drop it
            return False
        # 1. store into memory cache
        self.__cache.update(key=user, value=(content, msg), life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_login(user=user, content=content, msg=msg)
        # 3. save into local storage
        return self.__dos.save_login_command_message(user=user, content=content, msg=msg)

    # Override
    def login_command_message(self, user: ID) -> Tuple[Optional[LoginCommand], Optional[ReliableMessage]]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=user, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # login command message not load yet, wait to load
                self.__cache.update(key=user, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # login command message not exists
                    return None, None
                # login command message expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            cmd, msg = self.__redis.load_login(user=user)
            value = (cmd, msg)
            if cmd is None:
                # 3. check local storage
                cmd, msg = self.__dos.login_command_message(user=user)
                value = (cmd, msg)
                if cmd is not None:
                    # update redis server
                    self.__redis.save_login(user=user, content=cmd, msg=msg)
            # update memory cache
            self.__cache.update(key=user, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    def login_command(self, user: ID) -> Optional[LoginCommand]:
        cmd, _ = self.login_command_message(user=user)
        return cmd

    def login_message(self, user: ID) -> Optional[ReliableMessage]:
        _, msg = self.login_command_message(user=user)
        return msg
