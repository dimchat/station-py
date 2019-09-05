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
import random

from dimp import ID, Meta

from .storage import Storage


class MetaTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches = {}

    """
        Meta file for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/mkm/{ADDRESS}/meta.js'
        file path: '.dim/public/{ADDRESS}/meta.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', identifier.address, 'meta.js')

    def __cache_meta(self, meta: Meta, identifier: ID) -> bool:
        if meta.match_identifier(identifier):
            self.__caches[identifier] = meta
            return True

    def __load_meta(self, identifier: ID) -> Meta:
        path = self.__path(identifier=identifier)
        self.info('Loading meta from: %s' % path)
        dictionary = self.read_json(path=path)
        return Meta(dictionary)

    def __save_meta(self, meta: Meta, identifier: ID) -> bool:
        path = self.__path(identifier=identifier)
        if self.exists(path=path):
            # meta file already exists
            return True
        self.info('Saving meta into: %s' % path)
        return self.write_json(container=meta, path=path)

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        if not self.__cache_meta(meta=meta, identifier=identifier):
            # raise ValueError('failed to cache meta for ID: %s, %s' % (identifier, meta))
            self.error('failed to cache meta for ID: %s, %s' % (identifier, meta))
            return False
        return self.__save_meta(meta=meta, identifier=identifier)

    def meta(self, identifier: ID) -> Meta:
        # 1. get from cache
        info = self.__caches.get(identifier)
        if info is not None:
            return info
        # 2. load from storage
        info = self.__load_meta(identifier=identifier)
        if info is not None:
            # 3. update memory cache
            self.__caches[identifier] = info
            return info

    """
        Search Engine
        ~~~~~~~~~~~~~

        Search accounts by the 'Search Number'
    """

    def search(self, keywords: list) -> dict:
        results = {}
        max_count = 20
        array = self.scan_ids()
        array = random.sample(array, len(array))
        for identifier in array:
            network = identifier.type
            if not network.is_person():
                # ignore
                continue
            match = True
            for kw in keywords:
                if identifier.find(kw) < 0 and ('%010d' % identifier.number).find(kw) < 0:
                    # not match
                    match = False
                    break
            if not match:
                continue
            # got it
            meta = self.meta(identifier)
            if meta:
                results[identifier] = meta
                # force to stop
                max_count = max_count - 1
                if max_count <= 0:
                    break
        self.info('Got %d account(s) matched %s' % (len(results), keywords))
        return results

    def scan_ids(self) -> list:
        ids = []
        directory = os.path.join(self.root, 'public')
        # get all files in messages directory and sort by filename
        files = os.listdir(directory)
        for filename in files:
            path = os.path.join(directory, filename, 'meta.js')
            if not os.path.exists(path):
                # self.info('meta file not exists: %s' % path)
                continue
            address = self.identifier(filename)
            if address is None:
                # self.error('ID/address error: %s' % filename)
                continue
            meta = self.meta(identifier=address)
            if meta is None:
                self.error('meta error: %s' % address)
            else:
                # self.info('loaded meta for %s from %s: %s' % (identifier, path, meta))
                identifier = meta.generate_identifier(network=address.type)
                # the ID contains 'username' now
                if identifier != address:
                    # switch cache key
                    # self.__caches.pop(address)
                    self.__cache_meta(meta=meta, identifier=identifier)
                ids.append(identifier)
        self.info('Scanned %d ID(s) from %s' % (len(ids), directory))
        return ids
