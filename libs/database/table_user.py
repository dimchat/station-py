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

from typing import Optional, List, Dict

from dimsdk import ID, Command

from .redis import UserCache
from .dos import UserStorage

from .cache import CacheHolder, CachePool


class UserTable:

    def __init__(self):
        super().__init__()
        self.__redis = UserCache()
        self.__dos = UserStorage()
        # memory caches
        self.__contacts: Dict[ID, CacheHolder[List[ID]]] = CachePool.get_caches(name='contacts')
        self.__cmd_contacts: Dict[ID, CacheHolder[Command]] = CachePool.get_caches(name='cmd.contacts')
        self.__cmd_block: Dict[ID, CacheHolder[Command]] = CachePool.get_caches(name='cmd.block')
        self.__cmd_mute: Dict[ID, CacheHolder[Command]] = CachePool.get_caches(name='cmd.mute')

    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        # 1. save to memory cache
        self.__contacts[user] = CacheHolder(value=contacts)
        # 2. save to redis server
        self.__redis.save_contacts(contacts=contacts, user=user)
        # 3. save to local storage
        return self.__dos.save_contacts(contacts=contacts, user=user)

    def contacts(self, user: ID) -> List[ID]:
        # 1. check memory cache
        holder = self.__contacts.get(user)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__contacts[user] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            array = self.__redis.contacts(user=user)
            if len(array) == 0:
                # 3. check local storage
                array = self.__dos.contacts(user=user)
                if len(array) > 0:
                    # update redis server
                    self.__redis.save_contacts(contacts=array, user=user)
            # update memory cache
            holder = CacheHolder(value=array)
            self.__contacts[user] = holder
        # OK, return cached value
        return holder.value

    def save_contacts_command(self, content: Command, sender: ID) -> bool:
        # 1. update memory cache
        self.__cmd_contacts[sender] = CacheHolder(value=content)
        # 2. save to redis server
        self.__redis.save_contacts_command(content=content, sender=sender)
        # 3. save to local storage
        return self.__dos.save_contacts_command(content=content, sender=sender)

    def contacts_command(self, identifier: ID) -> Optional[Command]:
        # 1. check memory cache
        holder = self.__cmd_contacts.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__cmd_contacts[identifier] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            cmd = self.__redis.contacts_command(identifier=identifier)
            if cmd is None:
                # 3. check local storage
                cmd = self.__dos.contacts_command(identifier=identifier)
                if cmd is not None:
                    # update redis server
                    self.__redis.save_contacts_command(content=cmd, sender=identifier)
            # update memory cache
            holder = CacheHolder(value=cmd)
            self.__cmd_contacts[identifier] = holder
        # OK, return cached value
        return holder.value

    def save_block_command(self, content: Command, sender: ID) -> bool:
        # 1. update memory cache
        self.__cmd_block[sender] = CacheHolder(value=content)
        # 2. save to redis server
        self.__redis.save_block_command(content=content, sender=sender)
        # 3. save to local storage
        return self.__dos.save_block_command(content=content, sender=sender)

    def block_command(self, identifier: ID) -> Optional[Command]:
        # 1. check memory cache
        holder = self.__cmd_block.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__cmd_block[identifier] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            cmd = self.__redis.block_command(identifier=identifier)
            if cmd is None:
                # 3. check local storage
                cmd = self.__dos.block_command(identifier=identifier)
                if cmd is not None:
                    # update redis server
                    self.__redis.save_block_command(content=cmd, sender=identifier)
            # update memory cache
            holder = CacheHolder(value=cmd)
            self.__cmd_block[identifier] = holder
        # OK, return cached value
        return holder.value

    def save_mute_command(self, content: Command, sender: ID) -> bool:
        # 1. update memory cache
        self.__cmd_mute[sender] = CacheHolder(value=content)
        # 2. save to redis server
        self.__redis.save_mute_command(content=content, sender=sender)
        # 3. save to local storage
        return self.__dos.save_mute_command(content=content, sender=sender)

    def mute_command(self, identifier: ID) -> Optional[Command]:
        # 1. check memory cache
        holder = self.__cmd_mute.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__cmd_mute[identifier] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            cmd = self.__redis.mute_command(identifier=identifier)
            if cmd is None:
                # 3. check local storage
                cmd = self.__dos.mute_command(identifier=identifier)
                if cmd is not None:
                    # update redis server
                    self.__redis.save_mute_command(content=cmd, sender=identifier)
            # update memory cache
            holder = CacheHolder(value=cmd)
            self.__cmd_mute[identifier] = holder
        # OK, return cached value
        return holder.value
