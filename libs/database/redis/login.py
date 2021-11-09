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

import time
from typing import Optional

from dimp import json_encode, json_decode
from dimp import NetworkType, ID, ReliableMessage
from dimp import Command
from dimsdk import LoginCommand

from .base import Cache


class LoginCache(Cache):

    # login info cached in Redis will be expired after 10 hours, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 36000  # seconds

    @property  # Override
    def database(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def table(self) -> str:
        return 'user'

    """
        Login info for Users
        ~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.login'
    """
    def __login_key(self, identifier: ID) -> str:
        return '%s.%s.%s.login' % (self.database, self.table, identifier)

    def __save_login(self, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        dictionary = {'cmd': cmd.dictionary, 'msg': msg.dictionary}
        value = json_encode(o=dictionary)
        key = self.__login_key(identifier=msg.sender)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def __load_login(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        key = self.__login_key(identifier=identifier)
        value = self.get(name=key)
        if value is None:
            # data not exists
            return None, None
        dictionary = json_decode(data=value)
        cmd = dictionary.get('cmd')
        msg = dictionary.get('msg')
        if cmd is not None:
            cmd = LoginCommand(cmd)
        if msg is not None:
            msg = ReliableMessage.parse(msg=msg)
        return cmd, msg

    def save_login(self, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        # check sender
        sender = msg.sender
        if sender.type == NetworkType.STATION:
            # ignore station
            return False
        # check login time
        now = int(time.time())
        if now > cmd.time + self.EXPIRES:
            # expired command, drop it
            return False
        # save into redis server
        return self.__save_login(cmd=cmd, msg=msg)

    def login_info(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        cmd, msg = self.__load_login(identifier=identifier)
        if cmd is not None:
            now = int(time.time())
            if now > cmd.time + self.EXPIRES:
                # expired, ignore it
                return None, None
        return cmd, msg

    def login_command(self, identifier: ID) -> Optional[LoginCommand]:
        cmd, _ = self.login_info(identifier=identifier)
        return cmd

    def login_message(self, identifier: ID) -> Optional[ReliableMessage]:
        _, msg = self.login_info(identifier=identifier)
        return msg

    """
        Online / Offline
        ~~~~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.online'
        redis key: 'mkm.user.{ID}.offline'
    """
    def __online_key(self, identifier: ID) -> str:
        return '%s.%s.%s.online' % (self.database, self.table, identifier)

    def __offline_key(self, identifier: ID) -> str:
        return '%s.%s.%s.offline' % (self.database, self.table, identifier)

    def __save_command(self, key: str, cmd: Command) -> bool:
        # check login time
        now = int(time.time())
        if now > cmd.time + self.EXPIRES:
            # expired command, drop it
            return False
        dictionary = cmd.dictionary
        value = json_encode(o=dictionary)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def __load_command(self, key: str) -> Optional[Command]:
        value = self.get(name=key)
        if value is None:
            # data not exists
            return None
        dictionary = json_decode(data=value)
        if dictionary is None:
            # data error
            return None
        cmd = Command.parse(content=dictionary)
        if cmd is not None:
            now = int(time.time())
            if now > cmd.time + self.EXPIRES:
                # expired, ignore it
                return None
        return cmd

    def save_online(self, cmd: Command, msg: ReliableMessage) -> bool:
        # check sender
        sender = msg.sender
        if sender.type == NetworkType.STATION:
            # ignore station
            return False
        # save into redis
        key = self.__online_key(identifier=sender)
        return self.__save_command(key=key, cmd=cmd)

    def save_offline(self, cmd: Command, msg: ReliableMessage) -> bool:
        # check sender
        sender = msg.sender
        if sender.type == NetworkType.STATION:
            # ignore station
            return False
        # save into redis
        key = self.__offline_key(identifier=sender)
        return self.__save_command(key=key, cmd=cmd)

    def load_online(self, identifier: ID) -> Optional[Command]:
        key = self.__online_key(identifier=identifier)
        return self.__load_command(key=key)

    def load_offline(self, identifier: ID) -> Optional[Command]:
        key = self.__offline_key(identifier=identifier)
        return self.__load_command(key=key)
