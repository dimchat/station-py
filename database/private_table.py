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

from dimp import ID, PrivateKey

from .storage import Storage


class PrivateKeyTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches = {}

    """
        Private Key file for Local Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/secret.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'private', identifier.address, 'secret.js')

    def __cache_private_key(self, private_key: PrivateKey, identifier: ID) -> bool:
        assert private_key is not None and identifier.valid, 'private key error: %s, %s' % (identifier, private_key)
        self.__caches[identifier] = private_key
        return True

    def __load_private_key(self, identifier: ID) -> PrivateKey:
        path = self.__path(identifier=identifier)
        self.info('Loading private key from: %s' % path)
        dictionary = self.read_json(path=path)
        return PrivateKey(dictionary)

    def __save_private_key(self, private_key: PrivateKey, identifier: ID) -> bool:
        path = self.__path(identifier=identifier)
        if self.exists(path=path):
            # meta file already exists
            return True
        self.info('Saving private key into: %s' % path)
        return self.write_json(container=private_key, path=path)

    def save_private_key(self, private_key: PrivateKey, identifier: ID) -> bool:
        if not self.__cache_private_key(private_key=private_key, identifier=identifier):
            raise ValueError('failed to cache private key for ID: %s, %s' % (identifier, private_key))
            # self.error('failed to cache private key for ID: %s, %s' % (identifier, private_key))
            # return False
        return self.__save_private_key(private_key=private_key, identifier=identifier)

    def private_key(self, identifier: ID) -> PrivateKey:
        # 1. get from cache
        info = self.__caches.get(identifier)
        if info is not None:
            return info
        # 2. load from storage
        info = self.__load_private_key(identifier=identifier)
        if info is not None:
            # 3. update memory cache
            self.__caches[identifier] = info
            return info
