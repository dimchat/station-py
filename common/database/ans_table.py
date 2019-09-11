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

from dimp import ID

from .storage import Storage


class AddressNameTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: dict = None

    """
        Address Name Service
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/ans.txt'
    """
    def __path(self) -> str:
        return os.path.join(self.root, 'ans.txt')

    def __cache_record(self, name: str, identifier: ID) -> bool:
        if name is None or len(name) == 0:
            return False
        assert identifier.valid, 'ID not valid: %s' % identifier
        self.__caches[name] = identifier
        return True

    def __load_records(self) -> dict:
        path = self.__path()
        self.info('Loading ANS records from: %s' % path)
        dictionary = {}
        data = self.read_text(path=path)
        if data is not None:
            lines = data.splitlines()
            for record in lines:
                pair = record.split('\t')
                if len(pair) != 2:
                    self.error('invalid record: %s' % record)
                    continue
                k = pair[0]
                v = pair[1]
                dictionary[k] = self.identifier(v)
        return dictionary

    def __save_records(self, caches: dict) -> bool:
        text = ''
        keys = caches.keys()
        for k in keys:
            v = caches.get(k)
            if v is not None:
                text = text + k + '\t' + v + '\n'
        path = self.__path()
        self.info('Saving ANS records(%d) into: %s' % (len(keys), path))
        return self.write_text(text=text, path=path)

    def save_record(self, name: str, identifier: ID) -> bool:
        """ Save ANS record """
        if self.__caches is None:
            self.__caches = self.__load_records()
        # try to cache it
        if not self.__cache_record(name=name, identifier=identifier):
            return False
        # save to local storage
        caches = self.__caches.copy()
        return self.__save_records(caches=caches)

    def record(self, name: str) -> ID:
        """ Get ID by short name """
        if self.__caches is None:
            self.__caches = self.__load_records()
        return self.__caches.get(name)

    def names(self, identifier: ID) -> list:
        """ Get all short names with this ID """
        if self.__caches is None:
            self.__caches = self.__load_records()
        array = []
        caches = self.__caches.copy()
        keys = caches.keys()
        for k in keys:
            v = caches.get(k)
            if v == identifier:
                array.append(k)
        return array
