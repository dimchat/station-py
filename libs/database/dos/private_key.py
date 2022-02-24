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
from typing import Optional, List

from dimp import PrivateKey, DecryptKey, SignKey
from dimp import ID

from .base import Storage


class PrivateKeyStorage(Storage):

    META = 'M'
    VISA = 'V'

    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        if key_type == 'M':
            # save private key for meta
            path = self.__identity_key_path(identifier=identifier)
            self.info('Saving identity key into: %s' % path)
            return self.write_json(container=key.dictionary, path=path)
        # save private key for visa
        private_keys = self.__message_keys(identifier)
        private_keys = insert_private_key(key=key, private_keys=private_keys)
        if private_keys is None:
            # nothing changed
            return False
        plain = [item.dictionary for item in private_keys]
        # save into local storage
        path = self.__message_keys_path(identifier=identifier)
        self.info('Saving message keys into: %s' % path)
        return self.write_json(container=plain, path=path)

    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        keys: list = self.__message_keys(identifier=identifier)
        # the 'ID key' could be used for encrypting message too (RSA),
        # so we append it to the decrypt keys here
        id_key = self.__identity_key(identifier=identifier)
        if isinstance(id_key, DecryptKey) and id_key not in keys:
            # array = array.copy()
            keys.append(id_key)
        return keys

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        # TODO: support multi private keys
        return self.private_key_for_visa_signature(identifier=identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__identity_key(identifier=identifier)

    """
        Private Key file for Local Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        1. Identify Key - paired to meta.key, CONSTANT
            file path: '.dim/private/{ADDRESS}/secret.js'

        2. Message Key  - paired to visa.key, VOLATILE
            file path: '.dim/private/{ADDRESS}/secret_keys.js'
    """

    def __identity_key_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'private', str(identifier.address), 'secret.js')

    def __message_keys_path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'private', str(identifier.address), 'secret_keys.js')

    def __identity_key(self, identifier: ID) -> Optional[PrivateKey]:
        path = self.__identity_key_path(identifier=identifier)
        self.info('Loading identity key from: %s' % path)
        dictionary = self.read_json(path=path)
        return PrivateKey.parse(key=dictionary)

    def __message_keys(self, identifier: ID) -> List[PrivateKey]:
        keys = []
        path = self.__message_keys_path(identifier=identifier)
        self.info('Loading message keys from: %s' % path)
        array = self.read_json(path=path)
        if array is not None:
            for item in array:
                k = PrivateKey.parse(key=item)
                if k is not None:
                    keys.append(k)
        return keys


def insert_private_key(key: PrivateKey, private_keys: list) -> Optional[List[PrivateKey]]:
    index = find(item=key, array=private_keys)
    if index == 0:
        return None  # nothing changed
    elif index > 0:
        private_keys.pop(index)  # move to the front
    elif len(private_keys) > 2:
        private_keys.pop()  # keep only last three records
    private_keys.insert(0, key)
    return private_keys


def find(item, array: list) -> int:
    try:
        return array.index(item)
    except ValueError:
        return -1
