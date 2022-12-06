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

from dimples import ID, Command

from dimples.utils import CacheHolder, CacheManager
from dimples.database.t_user import UserTable as SuperTable

from ..common import BlockCommand, MuteCommand

from .redis import UserCache
from .dos import UserStorage


class UserTable(SuperTable):
    """ Implementations of UserDBI """

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__(root=root, public=public, private=private)
        self.__dos = UserStorage(root=root, public=public, private=private)
        self.__redis = UserCache()
        man = CacheManager()
        self.__cmd_contacts = man.get_pool(name='cmd.contacts')  # ID => StorageCommand
        self.__cmd_block = man.get_pool(name='cmd.block')        # ID => BlockCommand
        self.__cmd_mute = man.get_pool(name='cmd.mute')          # ID => MuteCommand

    def show_info(self):
        self.__dos.show_info()

    def save_contacts_command(self, content: Command, identifier: ID) -> bool:
        # 0. check old record with time
        old = self.contacts_command(identifier=identifier)
        if old is not None and old.time >= content.time > 0:
            # command expired, drop it
            return False
        # 1. store into memory cache
        self.__cmd_contacts.update(key=identifier, value=content, life_span=300)
        # 2. save to redis server
        self.__redis.save_contacts_command(content=content, identifier=identifier)
        # 3. save to local storage
        return self.__dos.save_contacts_command(content=content, identifier=identifier)

    def contacts_command(self, identifier: ID) -> Optional[Command]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cmd_contacts.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # storage command not load yet, wait to load
                self.__cmd_contacts.update(key=identifier, life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'storage cache error'
                if holder.is_alive(now=now):
                    # storage command not exists
                    return None
                # storage command expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check redis server
            value = self.__redis.contacts_command(identifier=identifier)
            if value is None:
                # 3. check local storage
                value = self.__dos.contacts_command(identifier=identifier)
                if value is not None:
                    # update redis server
                    self.__redis.save_contacts_command(content=value, identifier=identifier)
            # update memory cache
            self.__cmd_contacts.update(key=identifier, value=value, life_span=300, now=now)
        # OK, return cached value
        return value

    def save_block_command(self, content: BlockCommand, identifier: ID) -> bool:
        # 0. check old record with time
        old = self.block_command(identifier=identifier)
        if old is not None and old.time >= content.time > 0:
            # command expired, drop it
            return False
        # 1. store into memory cache
        self.__cmd_block.update(key=identifier, value=content, life_span=300)
        # 2. save to redis server
        self.__redis.save_block_command(content=content, identifier=identifier)
        # 3. save to local storage
        return self.__dos.save_block_command(content=content, identifier=identifier)

    def block_command(self, identifier: ID) -> Optional[BlockCommand]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cmd_block.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # block command not load yet, wait to load
                self.__cmd_block.update(key=identifier, life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'block cache error'
                if holder.is_alive(now=now):
                    # block command not exists
                    return None
                # block command expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check redis server
            value = self.__redis.block_command(identifier=identifier)
            if value is None:
                # 3. check local storage
                value = self.__dos.block_command(identifier=identifier)
                if value is not None:
                    # update redis server
                    self.__redis.save_block_command(content=value, identifier=identifier)
            # update memory cache
            self.__cmd_block.update(key=identifier, value=value, life_span=300, now=now)
        # OK, return cached value
        return value

    def save_mute_command(self, content: MuteCommand, identifier: ID) -> bool:
        # 0. check old record with time
        old = self.mute_command(identifier=identifier)
        if old is not None and old.time >= content.time > 0:
            # command expired, drop it
            return False
        # 1. store into memory cache
        self.__cmd_mute.update(key=identifier, value=content, life_span=300)
        # 2. save to redis server
        self.__redis.save_mute_command(content=content, identifier=identifier)
        # 3. save to local storage
        return self.__dos.save_mute_command(content=content, identifier=identifier)

    def mute_command(self, identifier: ID) -> Optional[MuteCommand]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cmd_mute.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # mute command not load yet, wait to load
                self.__cmd_mute.update(key=identifier, life_span=128, now=now)
            else:
                assert isinstance(holder, CacheHolder), 'mute cache error'
                if holder.is_alive(now=now):
                    # mute command not exists
                    return None
                # mute command expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. check redis server
            value = self.__redis.mute_command(identifier=identifier)
            if value is None:
                # 3. check local storage
                value = self.__dos.mute_command(identifier=identifier)
                if value is not None:
                    # update redis server
                    self.__redis.save_mute_command(content=value, identifier=identifier)
            # update memory cache
            self.__cmd_mute.update(key=identifier, value=value, life_span=300, now=now)
        # OK, return cached value
        return value
