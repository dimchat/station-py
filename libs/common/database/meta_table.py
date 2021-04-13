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
from typing import Optional, List, Dict

from dimp import NetworkType, ID, Meta

from .storage import Storage


class MetaTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: Dict[ID, Meta] = {}
        self.__empty = {'desc': 'just to avoid loading non-exists file again'}

    """
        Meta file for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/mkm/{ADDRESS}/meta.js'
        file path: '.dim/public/{ADDRESS}/meta.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'meta.js')

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        if not meta.match_identifier(identifier=identifier):
            # raise ValueError('meta not match: %s, %s' % (identifier, meta))
            self.error('meta not match: %s, %s' % (identifier, meta))
            return False
        # 0. check duplicate record
        old = self.meta(identifier=identifier)
        if old is not None:
            # meta won't change, no need to update
            return True
        # 1. store into memory cache
        self.__caches[identifier] = meta
        # 2. save into local storage
        path = self.__path(identifier=identifier)
        self.info('Saving meta into: %s' % path)
        return self.write_json(container=meta.dictionary, path=path)

    def meta(self, identifier: ID) -> Optional[Meta]:
        # 1. try from memory cache
        info = self.__caches.get(identifier)
        if info is None:
            # 2. try from local storage
            path = self.__path(identifier=identifier)
            self.info('Loading meta from: %s' % path)
            dictionary = self.read_json(path=path)
            info = Meta.parse(meta=dictionary)
            if info is None:
                # 2.1. place an empty meta for cache
                info = self.__empty
            # 3. store into memory cache
            self.__caches[identifier] = info
        if info is not self.__empty:
            return info
        self.error('meta not found: %s' % identifier)

    """
        Search Engine
        ~~~~~~~~~~~~~

        Search accounts by the 'Search Number'
    """

    def search(self, keywords: List[str], start: int = 0, limit: int = 20) -> dict:
        results = {}
        index = -1
        end = start + limit
        array = self.scan_ids()
        array = random.sample(array, len(array))
        for identifier in array:
            network = identifier.type
            if network not in [NetworkType.MAIN, NetworkType.BTC_MAIN, NetworkType.ROBOT]:
                # ignore
                continue
            string = str(identifier).lower()
            match = True
            for kw in keywords:
                if string.find(kw.lower()) < 0:
                    # not match
                    match = False
                    break
            if not match:
                continue
            meta = self.meta(identifier)
            if meta is None:
                # meta not found
                continue
            # got it
            index += 1
            if index < start:
                # skip
                continue
            elif index < end:
                # OK
                results[str(identifier)] = meta.dictionary
            else:
                # finished
                break
        self.info('Got %d account(s) matched %s' % (len(results), keywords))
        return results

    def scan_ids(self) -> List[ID]:
        ids = []
        directory = os.path.join(self.root, 'public')
        # get all files in messages directory and sort by filename
        files = os.listdir(directory)
        for filename in files:
            path = os.path.join(directory, filename, 'meta.js')
            if not os.path.exists(path):
                self.warning('meta file not exists: %s' % path)
                continue
            address = ID.parse(identifier=filename)
            if address is None:
                self.error('ID/address error: %s' % filename)
                continue
            meta = self.meta(identifier=address)
            if meta is None:
                self.error('meta error: %s' % address)
            else:
                identifier = meta.generate_identifier(network=address.type)
                self.debug('loaded meta for %s from %s: %s' % (identifier, path, meta))
                # the ID contains 'username' now
                if identifier != address:
                    # switch cache key
                    # self.__caches.pop(address)
                    self.__caches[identifier] = meta
                ids.append(identifier)
        self.debug('Scanned %d ID(s) from %s' % (len(ids), directory))
        return ids
