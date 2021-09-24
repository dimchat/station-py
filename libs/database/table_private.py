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

from typing import Optional, Dict, List

from dimp import ID, PrivateKey, SignKey, DecryptKey

from .dos.private_key import insert_private_key
from .dos import PrivateKeyStorage


class PrivateKeyTable:

    def __init__(self):
        super().__init__()
        self.__dos = PrivateKeyStorage()
        # memory caches
        self.__meta_private_keys: Dict[ID, PrivateKey] = {}
        self.__visa_private_keys: Dict[ID, List[PrivateKey]] = {}

    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        if key_type == 'M':
            self.__meta_private_keys[identifier] = key
        else:
            private_keys = self.__visa_private_keys.get(identifier)
            if private_keys is None or len(private_keys) == 0:
                self.__visa_private_keys[identifier] = [key]
            else:
                insert_private_key(key=key, private_keys=private_keys)
        return self.__dos.save_private_key(key=key, identifier=identifier, key_type=key_type)

    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        # check memory cache
        array: list = self.__visa_private_keys.get(identifier)
        if array is None:
            # check local storage
            array = self.__dos.private_keys_for_decryption(identifier=identifier)
            if array is None:
                array = []
            self.__visa_private_keys[identifier] = array
        key = self.__meta_private_keys.get(identifier)
        if isinstance(key, DecryptKey) and key not in array:
            array = array.copy()
            array.append(key)
        if len(array) > 0:
            return array
        # cache in memory cache
        return array

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        # TODO: support multi private keys
        return self.private_key_for_visa_signature(identifier=identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        key = self.__meta_private_keys.get(identifier)
        if key is None:
            key = self.__dos.private_key_for_visa_signature(identifier=identifier)
            if isinstance(key, PrivateKey):
                self.__meta_private_keys[identifier] = key
        return key
