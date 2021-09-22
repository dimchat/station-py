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
import json
import os
from typing import Optional, Dict

from dimp import ID, Meta

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

    def __save_json(self, identifier: ID, dictionary: dict) -> bool:
        path = self.__path(identifier=identifier)
        self.info('Saving meta into: %s' % path)
        return self.write_json(container=dictionary, path=path)

    def __load_json(self, identifier: ID) -> Optional[Meta]:
        path = self.__path(identifier=identifier)
        self.info('Loading meta from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return Meta.parse(meta=dictionary)

    def __save_redis(self, identifier: ID, dictionary: dict):
        info = json.dumps(dictionary)
        self.redis.hset(name='mkm.metas', key=str(identifier), value=info)

    def __load_redis(self, identifier: ID) -> Optional[Meta, dict]:
        info = self.redis.hget(name='mkm.metas', key=str(identifier))
        if info is None:
            return None
        dictionary = json.loads(info)
        if dictionary is None:
            return self.__empty
        if 'type' not in dictionary and 'version' not in dictionary:
            return self.__empty
        if 'key' not in dictionary:
            return self.__empty
        # OK
        return Meta.parse(meta=dictionary)

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
        # 2. store into redis server
        dictionary = meta.dictionary
        self.__save_redis(identifier=identifier, dictionary=dictionary)
        # 3. save into local storage
        return self.__save_json(identifier=identifier, dictionary=dictionary)

    def meta(self, identifier: ID) -> Optional[Meta]:
        # 1. try from memory cache
        info = self.__caches.get(identifier)
        if info is not None:
            # got from memory cache
            return info
        # 2. try from redis server
        info = self.__load_redis(identifier=identifier)
        if info is not None and info is not self.__empty:
            # got from redis server, store it into memory cache now
            self.__caches[identifier] = info
            return info
        # 3. try from local storage
        info = self.__load_json(identifier=identifier)
        if info is not None:
            # got from local storage, store it into redis server & memory cache
            self.__save_redis(identifier=identifier, dictionary=info.dictionary)
            self.__caches[identifier] = info
            return info
        else:
            # file not found, place an empty meta for cache
            self.__save_redis(identifier=identifier, dictionary=self.__empty)
            self.error('meta not found: %s' % identifier)
