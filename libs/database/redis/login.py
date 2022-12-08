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

from typing import Optional, Set, Tuple

from dimples import json_encode, json_decode, utf8_encode, utf8_decode
from dimples import ID, ReliableMessage

from ...common import LoginCommand

from .base import Cache


class LoginCache(Cache):

    # login info cached in Redis will be expired after 10 hours, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 36000  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def tbl_name(self) -> str:
        return 'user'

    """
        Login info for Users
        ~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.user.{ID}.login'
    """
    def __login_key(self, identifier: ID) -> str:
        return '%s.%s.%s.login' % (self.db_name, self.tbl_name, identifier)

    def save_login(self, identifier: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        """ Save login command & message into Redis Server """
        dictionary = {'cmd': content.dictionary, 'msg': msg.dictionary}
        js = json_encode(obj=dictionary)
        value = utf8_encode(string=js)
        key = self.__login_key(identifier=identifier)
        self.set(name=key, value=value, expires=self.EXPIRES)
        return True

    def load_login(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        key = self.__login_key(identifier=identifier)
        value = self.get(name=key)
        if value is None:
            # data not exists
            return None, None
        js = utf8_decode(data=value)
        dictionary = json_decode(string=js)
        cmd = dictionary.get('cmd')
        msg = dictionary.get('msg')
        if cmd is not None:
            cmd = LoginCommand(cmd)
        return cmd, ReliableMessage.parse(msg=msg)

    def login_command(self, identifier: ID) -> Optional[LoginCommand]:
        cmd, _ = self.load_login(identifier=identifier)
        return cmd

    def login_message(self, identifier: ID) -> Optional[ReliableMessage]:
        _, msg = self.load_login(identifier=identifier)
        return msg

    """
        Session Online
        ~~~~~~~~~~~~~~

        redis key: 'mkm.user.active_sockets'
    """
    def __active_sockets_key(self) -> str:
        return '%s.%s.active_sockets' % (self.db_name, self.tbl_name)

    def save_socket_addresses(self, identifier: ID, addresses: Set[Tuple[str, int]]) -> bool:
        name = self.__active_sockets_key()
        value = serialize_socket_addresses(addresses=addresses)
        if value is None:
            return self.hdel(name=name, key=str(identifier))
        return self.hset(name=name, key=str(identifier), value=value)

    def socket_addresses(self, identifier: ID) -> Set[Tuple[str, int]]:
        name = self.__active_sockets_key()
        value = self.hget(name=name, key=str(identifier))
        if is_empty(value=value):
            return set()
        return deserialize_socket_addresses(value=value)

    def all_users(self) -> Set[ID]:
        name = self.__active_sockets_key()
        all_keys = self.hkeys(name=name)
        users = set()
        for key in all_keys:
            identifier = ID.parse(identifier=key)
            if identifier is None:
                # should not happen
                continue
            users.add(identifier)
        return users

    def active_users(self) -> Set[ID]:
        name = self.__active_sockets_key()
        records = self.hgetall(name=name)  # ID => Set[socket_address]
        if records is None:
            return set()
        users = set()
        for key in records:
            value = records[key]
            if is_empty(value=value):
                # user logout
                continue
            string = utf8_decode(data=key)
            identifier = ID.parse(identifier=string)
            if identifier is None:
                # should not happen
                continue
            users.add(identifier)
        return users


"""
    JsON format: [
        [host, port],
        [host, port],
        [host, port]
    ]
"""


def serialize_socket_addresses(addresses: Set[Tuple[str, int]]) -> Optional[bytes]:
    if addresses is None or len(addresses) == 0:
        return None
    array = []
    for add in addresses:
        item = [add[0], add[1]]
        array.append(item)
    js = json_encode(obj=array)
    return utf8_encode(string=js)


def deserialize_socket_addresses(value: bytes) -> Set[Tuple[str, int]]:
    js = utf8_decode(data=value)
    array = json_decode(string=js)
    all_addresses = set()
    for item in array:
        address = (item[0], item[1])
        all_addresses.add(address)
    return all_addresses


min_len = len('[["8.8.8.8",8]]')


def is_empty(value: bytes) -> bool:
    return value is None or len(value) <= 2  # < min_len
