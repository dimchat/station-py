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

from typing import Optional, Dict

from dimp import ID, ReliableMessage
from dimsdk import LoginCommand

from .redis import LoginCache

from .cache import CacheHolder, CachePool


class LoginTable:

    def __init__(self):
        super().__init__()
        self.__redis = LoginCache()
        # memory caches
        self.__caches: Dict[ID, CacheHolder[tuple]] = CachePool.get_caches(name='login')

    def save_login(self, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        if self.__redis.save_login(cmd=cmd, msg=msg):
            self.__caches[msg.sender] = CacheHolder(value=(cmd, msg), life_span=300)
            return True

    def login_command(self, identifier: ID) -> Optional[LoginCommand]:
        cmd, _ = self.login_info(identifier=identifier)
        return cmd

    def login_message(self, identifier: ID) -> Optional[ReliableMessage]:
        _, msg = self.login_info(identifier=identifier)
        return msg

    def login_info(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        # 1. check memory cache
        holder = self.__caches.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__caches[identifier] = CacheHolder(value=(None, None), life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            cmd, msg = self.__redis.login_info(identifier=identifier)
            # update memory cache
            holder = CacheHolder(value=(cmd, msg), life_span=300)
            self.__caches[identifier] = holder
        # OK, return cached value
        return holder.value
