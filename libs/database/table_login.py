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
from dimp import Command
from dimsdk import LoginCommand

from .redis import LoginCache

from .cache import CacheHolder, CachePool


class LoginTable:

    def __init__(self):
        super().__init__()
        self.__redis = LoginCache()
        # memory caches
        self.__logins: Dict[ID, CacheHolder[tuple]] = CachePool.get_caches(name='login')
        self.__online: Dict[ID, CacheHolder[Command]] = CachePool.get_caches(name='online')
        self.__offline: Dict[ID, CacheHolder[Command]] = CachePool.get_caches(name='offline')

    def save_login(self, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        sender = msg.sender
        assert sender == cmd.identifier, 'sender error: %s, %s' % (sender, cmd.identifier)
        login_time = cmd.time
        assert login_time is not None, 'login command error: %s' % cmd
        # check exists command
        old = self.login_command(identifier=sender)
        if old is not None:
            old_time = old.time
            assert old_time is not None, 'old command error: %s' % old
            if old_time > login_time:
                # expired command, drop it
                return False
            elif old_time == login_time:
                # same command, return True to post notification
                return True
        # save into redis
        if self.__redis.save_login(cmd=cmd, msg=msg):
            self.__logins[msg.sender] = CacheHolder(value=(cmd, msg), life_span=300)
            return True

    def login_command(self, identifier: ID) -> Optional[LoginCommand]:
        cmd, _ = self.login_info(identifier=identifier)
        return cmd

    def login_message(self, identifier: ID) -> Optional[ReliableMessage]:
        _, msg = self.login_info(identifier=identifier)
        return msg

    def login_info(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        # 1. check memory cache
        holder = self.__logins.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__logins[identifier] = CacheHolder(value=(None, None), life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            cmd, msg = self.__redis.login_info(identifier=identifier)
            # update memory cache
            holder = CacheHolder(value=(cmd, msg), life_span=300)
            self.__logins[identifier] = holder
        # OK, return cached value
        return holder.value

    #
    #   Online/Offline
    #
    def save_online(self, cmd: Command, msg: ReliableMessage) -> bool:
        sender = msg.sender
        online_time = cmd.time
        assert online_time is not None, 'online command error: %s' % cmd
        # check exists command
        old = self.online_command(identifier=sender)
        if old is None:
            old_time = 0
        else:
            old_time = old.time
            assert old_time is not None, 'old command error: %s' % old
        if online_time < old_time:
            # expired command, drop it
            return False
        # check with offline time
        offline = self.offline_command(identifier=sender)
        if offline is None:
            offline_time = 0
        else:
            offline_time = offline.time
            assert offline_time is not None, 'offline command error: %s' % old
        if online_time == old_time:
            # same command, return True to post notification
            return online_time >= offline_time
        elif online_time < offline_time:
            # expired command, drop it
            return False
        # save into redis
        if self.__redis.save_online(cmd=cmd, msg=msg):
            self.__online[msg.sender] = CacheHolder(value=cmd, life_span=300)
            return True

    def save_offline(self, cmd: Command, msg: ReliableMessage) -> bool:
        sender = msg.sender
        offline_time = cmd.time
        assert offline_time is not None, 'offline command error: %s' % cmd
        # check exists command
        old = self.offline_command(identifier=sender)
        if old is None:
            old_time = 0
        else:
            old_time = old.time
            assert old_time is not None, 'old command error: %s' % old
        if offline_time < old_time:
            # expired command, drop it
            return False
        # check with online time
        online = self.online_command(identifier=sender)
        if online is None:
            online_time = 0
        else:
            online_time = online.time
            assert online_time is not None, 'online command error: %s' % old
        if offline_time == old_time:
            # same command, return True to post notification
            return offline_time >= online_time
        elif offline_time < online_time:
            # expired command, drop it
            return False
        # save into redis
        if self.__redis.save_offline(cmd=cmd, msg=msg):
            self.__offline[msg.sender] = CacheHolder(value=cmd, life_span=300)
            return True

    def online_command(self, identifier: ID) -> Optional[Command]:
        # 1. check memory cache
        holder = self.__online.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                empty: Optional[Command] = None
                self.__online[identifier] = CacheHolder(value=empty, life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            cmd = self.__redis.load_online(identifier=identifier)
            # update memory cache
            holder = CacheHolder(value=cmd, life_span=300)
            self.__online[identifier] = holder
        # OK, return cached value
        return holder.value

    def offline_command(self, identifier: ID) -> Optional[Command]:
        # 1. check memory cache
        holder = self.__offline.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                empty: Optional[Command] = None
                self.__offline[identifier] = CacheHolder(value=empty, life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            cmd = self.__redis.load_offline(identifier=identifier)
            # update memory cache
            holder = CacheHolder(value=cmd, life_span=300)
            self.__offline[identifier] = holder
        # OK, return cached value
        return holder.value
