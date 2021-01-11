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
from typing import Optional, List, Dict

from dimp import ID, ANYONE, EVERYONE

from .storage import Storage


class AddressNameTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: Dict[str, ID] = None

    """
        Address Name Service
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/ans.txt'
    """
    def __path(self) -> str:
        return os.path.join(self.root, 'ans.txt')

    def __load_records(self) -> Dict[str, ID]:
        path = self.__path()
        self.info('Loading ANS records from: %s' % path)
        dictionary = {}
        text = self.read_text(path=path)
        if text is not None:
            lines = text.splitlines()
            for record in lines:
                pair = record.split('\t')
                if len(pair) != 2:
                    self.error('invalid record: %s' % record)
                    continue
                k = pair[0]
                v = pair[1]
                dictionary[k] = ID.parse(identifier=v)
        #
        #  Reserved names
        #
        dictionary['all'] = EVERYONE
        dictionary[EVERYONE.name] = EVERYONE
        dictionary[ANYONE.name] = ANYONE
        dictionary['owner'] = ANYONE
        dictionary['founder'] = ID.parse(identifier='moky@4DnqXWdTV8wuZgfqSCX9GjE2kNq7HJrUgQ')  # 'Albert Moky'
        return dictionary

    def __save_records(self, caches: Dict[str, ID]) -> bool:
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
        if name is None or len(name) == 0 or identifier is None:
            return False
        if self.__caches is None:
            self.__caches = self.__load_records()
        # store into memory cache
        self.__caches[name] = identifier
        # store into local storage
        return self.__save_records(caches=self.__caches.copy())

    def record(self, name: str) -> Optional[ID]:
        """ Get ID by short name """
        if self.__caches is None:
            self.__caches = self.__load_records()
        return self.__caches.get(name)

    def names(self, identifier: ID) -> List[str]:
        """ Get all short names with this ID """
        if self.__caches is None:
            self.__caches = self.__load_records()
        # all names
        if '*' == identifier:
            return list(self.__caches.keys())
        # get keys with the same value
        caches = self.__caches.copy()
        array = []
        for k in caches:
            v = caches[k]
            if v == identifier:
                array.append(k)
        return array
