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

import os
from typing import Optional, Dict, List

from dimp import ID, PrivateKey, SignKey, DecryptKey

from .storage import Storage


class PrivateKeyTable(Storage):

    META = 'M'
    VISA = 'V'

    def __init__(self):
        super().__init__()
        # memory caches
        self.__meta_private_keys: Dict[ID, PrivateKey] = {}
        self.__visa_private_keys: Dict[ID, List[PrivateKey]] = {}
        self.__empty = {'desc': 'just to avoid loading non-exists file again'}

    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str='M'):
        if key_type == 'M':
            return self.__save_identify_key(key=key, identifier=identifier)
        else:
            return self.__save_message_key(key=key, identifier=identifier)

    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        array: list = self.__message_keys(identifier=identifier)
        key = self.__identity_key(identifier=identifier)
        if isinstance(key, DecryptKey) and key not in array:
            array = array.copy()
            array.append(key)
        return array

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        # TODO: support multi private keys
        return self.private_key_for_visa_signature(identifier=identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__identity_key(identifier=identifier)

    """
        Private Key file for Local Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        1. Identify Key - paired to meta.key, CONSTANT
        2. Message Key  - paired to visa.key, VOLATILE

        file path: '.dim/private/{ADDRESS}/secret.js'
    """
    def __identity_key_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'private', str(identifier.address), 'secret.js')

    def __message_keys_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'private', str(identifier.address), 'secret_keys.js')

    def __identity_key(self, identifier: ID) -> Optional[PrivateKey]:
        # 1. try from memory cache
        key = self.__meta_private_keys.get(identifier)
        if key is None:
            # 2. try from local storage
            path = self.__identity_key_path(identifier=identifier)
            self.info('Loading identity key from: %s' % path)
            dictionary = self.read_json(path=path)
            key = PrivateKey.parse(key=dictionary)
            if key is None:
                # 2.1. place an empty key for cache
                key = self.__empty
            # 3. store into memory cache
            self.__meta_private_keys[identifier] = key
        if key is not self.__empty:
            return key
        self.error('private key not found: %s' % identifier)

    def __message_keys(self, identifier: ID) -> List[PrivateKey]:
        # 1. try from memory cache
        keys = self.__visa_private_keys.get(identifier)
        if keys is None:
            keys = []
            # 2. try from local storage
            path = self.__message_keys_path(identifier=identifier)
            self.info('Loading message keys from: %s' % path)
            array = self.read_json(path=path)
            if array is not None:
                for item in array:
                    k = PrivateKey.parse(key=item)
                    if k is not None:
                        keys.append(k)
            # 3. store into memory cache
            self.__visa_private_keys[identifier] = keys
        return keys

    def __cache_identity_key(self, identifier: ID, key: PrivateKey) -> bool:
        old = self.__identity_key(identifier=identifier)
        if old is None:
            self.__meta_private_keys[identifier] = key
            return True

    def __cache_message_key(self, key: PrivateKey, identifier: ID) -> bool:
        array = self.__message_keys(identifier=identifier)
        index = find(item=key, array=array)
        if index == 0:
            return False      # nothing changed
        elif index > 0:
            array.pop(index)  # move to the front
        elif len(array) > 2:
            array.pop()       # keep only last three records
        array.insert(0, key)
        self.__visa_private_keys[identifier] = array
        return True

    def __save_identify_key(self, key: PrivateKey, identifier: ID) -> bool:
        # 1. try to store into memory cache
        if self.__cache_identity_key(key=key, identifier=identifier):
            # 2. save into local storage
            path = self.__identity_key_path(identifier=identifier)
            self.info('Saving identity key into: %s' % path)
            return self.write_json(container=key.dictionary, path=path)

    def __save_message_key(self, key: PrivateKey, identifier: ID) -> bool:
        # 1. try to store into memory cache
        if self.__cache_message_key(key=key, identifier=identifier):
            array = self.__message_keys(identifier).copy()
            plain = [item.dictionary for item in array]
            # 2. save into local storage
            path = self.__message_keys_path(identifier=identifier)
            self.info('Saving message keys into: %s' % path)
            return self.write_json(container=plain, path=path)


def find(item, array: list) -> int:
    try:
        return array.index(item)
    except ValueError:
        return -1
