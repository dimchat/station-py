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

from dimsdk import json_encode, json_decode, utf8_encode, utf8_decode
from dimsdk import NetworkType, ID, ReliableMessage
from dimsdk import Content, Command

# from ...common import LoginCommand

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

    def __save_login(self, content: Command, msg: ReliableMessage) -> bool:
        dictionary = {'cmd': content.dictionary, 'msg': msg.dictionary}
        value = json_encode(obj=dictionary)
        value = utf8_encode(string=value)
        key = self.__login_key(identifier=msg.sender)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def __load_login(self, identifier: ID) -> (Optional[Command], Optional[ReliableMessage]):
        key = self.__login_key(identifier=identifier)
        value = self.get(name=key)
        if value is None:
            # data not exists
            return None, None
        value = utf8_decode(data=value)
        dictionary = json_decode(string=value)
        cmd = dictionary.get('cmd')
        msg = dictionary.get('msg')
        if cmd is not None:
            from ...common import LoginCommand
            cmd = LoginCommand(cmd)
        if msg is not None:
            msg = ReliableMessage.parse(msg=msg)
        return cmd, msg

    def save_login(self, content: Command, msg: ReliableMessage) -> bool:
        # check sender
        sender = msg.sender
        if sender.type == NetworkType.STATION:
            # ignore station
            return False
        # check login time
        now = int(time.time())
        if now > content.time + self.EXPIRES:
            # expired command, drop it
            return False
        # save into redis server
        return self.__save_login(content=content, msg=msg)

    def login_info(self, identifier: ID) -> (Optional[Command], Optional[ReliableMessage]):
        cmd, msg = self.__load_login(identifier=identifier)
        if cmd is not None:
            now = int(time.time())
            if now > cmd.time + self.EXPIRES:
                # expired, ignore it
                return None, None
        return cmd, msg

    def login_command(self, identifier: ID) -> Optional[Command]:
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

    def __save_command(self, key: str, content: Command) -> bool:
        # check login time
        now = int(time.time())
        if now > content.time + self.EXPIRES:
            # expired command, drop it
            return False
        dictionary = content.dictionary
        value = json_encode(obj=dictionary)
        value = utf8_encode(string=value)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def __load_command(self, key: str) -> Optional[Command]:
        value = self.get(name=key)
        if value is None:
            # data not exists
            return None
        value = utf8_decode(data=value)
        dictionary = json_decode(string=value)
        if dictionary is None:
            # data error
            return None
        cmd = Content.parse(content=dictionary)
        if cmd is not None:
            now = int(time.time())
            if now > cmd.time + self.EXPIRES:
                # expired, ignore it
                return None
        return cmd

    def save_online(self, content: Command, msg: ReliableMessage) -> bool:
        # check sender
        sender = msg.sender
        if sender.type == NetworkType.STATION:
            # ignore station
            return False
        # save into redis
        key = self.__online_key(identifier=sender)
        return self.__save_command(key=key, content=content)

    def save_offline(self, content: Command, msg: ReliableMessage) -> bool:
        # check sender
        sender = msg.sender
        if sender.type == NetworkType.STATION:
            # ignore station
            return False
        # save into redis
        key = self.__offline_key(identifier=sender)
        return self.__save_command(key=key, content=content)

    def load_online(self, identifier: ID) -> Optional[Command]:
        key = self.__online_key(identifier=identifier)
        return self.__load_command(key=key)

    def load_offline(self, identifier: ID) -> Optional[Command]:
        key = self.__offline_key(identifier=identifier)
        return self.__load_command(key=key)
