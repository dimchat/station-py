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
from typing import Optional

from dimsdk import ID, ReliableMessage

from dimples.utils import CacheHolder, CacheManager
from dimples.common import LoginDBI
from dimples.common import LoginCommand

from .redis import LoginCache
from .dos import LoginStorage


class LoginTable(LoginDBI):
    """ Implementations of LoginDBI """

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
    def save_login_command_message(self, identifier: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        assert identifier == msg.sender, 'msg sender not match: %s => %s' % (identifier, msg.sender)
        assert identifier == content.identifier, 'cmd ID not match: %s => %s' % (identifier, content.identifier)
        # 0. check old record with time
        old, _ = self.login_command_message(identifier=identifier)
        if old is not None and old.time >= content.time > 0:
            # command expired, drop it
            return False
        # 1. store into memory cache
        self.__cache.update(key=identifier, value=(content, msg), life_span=300)
        # 2. store into redis server
        self.__redis.save_login(identifier=identifier, content=content, msg=msg)
        # 3. save into local storage
        return self.__dos.save_login_command_message(identifier=identifier, content=content, msg=msg)

    # Override
    def login_command_message(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # login command message not load yet, wait to load
                self.__cache.update(key=identifier, life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'login cache error'
                if holder.is_alive(now=now):
                    # login command message not exists
                    return None
                # login command message expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check redis server
            cmd, msg = self.__redis.load_login(identifier=identifier)
            value = (cmd, msg)
            if cmd is None:
                # 3. check local storage
                cmd, msg = self.__dos.login_command_message(identifier=identifier)
                value = (cmd, msg)
                if cmd is not None:
                    # update redis server
                    self.__redis.save_login(identifier=identifier, content=cmd, msg=msg)
            # update memory cache
            self.__cache.update(key=identifier, value=value, life_span=300, now=now)
        # OK, return cached value
        return value

    def login_command(self, identifier: ID) -> Optional[LoginCommand]:
        cmd, _ = self.login_command_message(identifier=identifier)
        return cmd

    def login_message(self, identifier: ID) -> Optional[ReliableMessage]:
        _, msg = self.login_command_message(identifier=identifier)
        return msg
