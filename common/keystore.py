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

from dimp import ID, SymmetricKey
from dimp import KeyStore as KeyCache

from .log import Log


class KeyStore(KeyCache):

    def __init__(self):
        super().__init__()
        # memory cache
        self.__metas = {}
        self.__profiles = {}
        self.__private_keys = {}

        self.user = None
        self.base_dir = '/tmp/.dim/'

    def __directory(self, control: str, identifier: ID, sub_dir: str = '') -> str:
        path = self.base_dir + control + '/' + identifier.address
        if sub_dir:
            path = path + '/' + sub_dir
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def cipher_key(self, sender: ID, receiver: ID) -> SymmetricKey:
        key = super().cipher_key(sender=sender, receiver=receiver)
        if key is not None:
            return key
        # create a new key & save it into the Key Store
        key = SymmetricKey({'algorithm': 'AES'})
        self.cache_cipher_key(key=key, sender=sender, receiver=receiver)
        return key

    def flush(self):
        if self.dirty is False or self.user is None:
            return
        # write key table to persistent storage
        directory = self.__directory('public', self.user.identifier)
        path = directory + '/keystore.js'
        with open(path, 'w') as file:
            file.write(self.key_table)
        Log.info('[DB] keystore write into file: %s' % path)
        self.dirty = False

    def key_exists(self, sender_address: str, receiver_address: str) -> bool:
        key_map = self.key_table.get(sender_address)
        if key_map is None:
            return False
        return receiver_address in key_map

    def reload(self) -> bool:
        if self.user is None:
            return False
        # load key table from persistent storage
        directory = self.__directory('public', self.user.identifier)
        path = directory + '/keystore.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
            table_ = json.loads(data)
            # key_table[sender.address] -> key_map
            for from_, map_ in table_:
                key_map = self.key_table.get(from_)
                if key_map is None:
                    key_map = {}
                    self.key_table[from_] = key_map
                # key_map[receiver.address] -> key
                for to_, key_ in map_:
                    # update memory cache
                    key_map[to_] = SymmetricKey(key_)


keystore = KeyStore()
