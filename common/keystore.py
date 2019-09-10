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

"""
    Key Store
    ~~~~~~~~~

    Memory cache for reused passwords (symmetric key)
"""

import os
import json

from dimp import ID, SymmetricKey, LocalUser
from dimp import KeyCache

from .utils import Log


class KeyStore(KeyCache):

    def __init__(self):
        self.__user: LocalUser = None
        self.__base_dir: str = '/tmp/.dim/'
        super().__init__()

    @property
    def user(self) -> LocalUser:
        return self.__user

    @user.setter
    def user(self, value: LocalUser):
        if value is None:
            # save key map for old user
            self.flush()
            self.__user = None
        elif value != self.__user:
            # load key map for new user
            self.__user = value
            self.update_keys(self.load_keys())

    @property
    def directory(self) -> str:
        return self.__base_dir

    @directory.setter
    def directory(self, value: str):
        self.__base_dir = value

    def __directory(self, control: str, identifier: ID, sub_dir: str = None) -> str:
        path = self.__base_dir + control + '/' + identifier.address
        if sub_dir:
            path = path + '/' + sub_dir
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def __path(self) -> str:
        if self.__user is not None:
            directory = self.__directory('public', self.__user.identifier)
            return directory + '/keystore.js'

    def save_keys(self, key_map: dict) -> bool:
        # write key table to persistent storage
        path = self.__path()
        if path is None:
            return False
        with open(path, 'w') as file:
            file.write(json.dumps(key_map))
            Log.info('[DB] keystore write into file: %s' % path)
            return True

    def load_keys(self) -> dict:
        # load key table from persistent storage
        path = self.__path()
        if path is not None and os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                return json.loads(data)

    #
    #   ICipherKeyDataSource
    #
    def cipher_key(self, sender: ID, receiver: ID) -> SymmetricKey:
        key = super().cipher_key(sender=sender, receiver=receiver)
        if key is None:
            # create a new key & save it into the Key Store
            key = SymmetricKey({'algorithm': 'AES'})
            self.cache_cipher_key(key=key, sender=sender, receiver=receiver)
        return key

    def reuse_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID) -> SymmetricKey:
        # TODO: check reuse key
        pass
