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

from typing import Optional, Union, Dict, List

from dimp import ID, PrivateKey, SignKey, DecryptKey

from .dos.private_key import insert_private_key
from .dos import PrivateKeyStorage

from .cache import CacheHolder, CachePool


class PrivateKeyTable:

    def __init__(self):
        super().__init__()
        self.__dos = PrivateKeyStorage()
        # memory caches
        self.__id_keys: Dict[ID, CacheHolder[Union[PrivateKey, SignKey]]] =\
            CachePool.get_caches(name='private.id.keys')
        self.__msg_keys: Dict[ID, CacheHolder[List[Union[PrivateKey, DecryptKey]]]] =\
            CachePool.get_caches(name='private.msg.keys')

    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        # 1. update memory cache
        if key_type == 'M':
            # update 'id.keys'
            self.__id_keys[identifier] = CacheHolder(value=key, life_span=36000)
        else:
            # get old keys
            private_keys = self.private_keys_for_decryption(identifier=identifier)
            private_keys = insert_private_key(key=key, private_keys=private_keys)
            if private_keys is None:
                # key already exists, nothing changed
                return False
            # update 'msg.keys'
            self.__msg_keys[identifier] = CacheHolder(value=private_keys, life_span=36000)
        # 2. update local storage
        return self.__dos.save_private_key(key=key, identifier=identifier, key_type=key_type)

    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        # 1. check memory cache
        holder = self.__msg_keys.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__msg_keys[identifier] = CacheHolder(value=[], life_span=128)
            else:
                holder.renewal()
            # 2. check local storage
            private_keys = self.__dos.private_keys_for_decryption(identifier=identifier)
            # the 'ID key' could be used for encrypting message too (RSA),
            # so we append it to the decrypt keys here
            id_key = self.private_key_for_visa_signature(identifier=identifier)
            if isinstance(id_key, DecryptKey) and id_key not in private_keys:
                private_keys = private_keys.copy()
                private_keys.append(id_key)
            # update memory cache
            holder = CacheHolder(value=private_keys, life_span=36000)
            self.__msg_keys[identifier] = holder
        # OK, return cached value
        return holder.value

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        # TODO: support multi private keys
        return self.private_key_for_visa_signature(identifier=identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        # 1. check memory cache
        holder = self.__id_keys.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__id_keys[identifier] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check local storage
            key = self.__dos.private_key_for_visa_signature(identifier=identifier)
            # update cache
            holder = CacheHolder(value=key, life_span=36000)
            self.__id_keys[identifier] = holder
        # OK, return cached value
        return holder.value
