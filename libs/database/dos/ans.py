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
from typing import Dict

from dimp import ID, ANYONE, EVERYONE

from .base import Storage


class AddressNameStorage(Storage):
    """
        Address Name Service
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/ans.txt'
    """
    def __path(self) -> str:
        return os.path.join(self.root, 'ans.txt')

    def load_records(self) -> Dict[str, ID]:
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

    def save_records(self, records: Dict[str, ID]) -> bool:
        text = ''
        keys = records.keys()
        for k in keys:
            v = records.get(k)
            if v is not None:
                text = text + k + '\t' + v + '\n'
        path = self.__path()
        self.info('Saving ANS records(%d) into: %s' % (len(keys), path))
        return self.write_text(text=text, path=path)
