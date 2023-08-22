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

from typing import Dict

from dimples import ID, ANYONE, EVERYONE, FOUNDER

from dimples.database.dos.base import template_replace
from dimples.database.dos import Storage


class AddressNameStorage(Storage):
    """
        Address Name Service
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/ans.js'
    """
    ans_path = '{PRIVATE}/ans.js'

    def show_info(self):
        path = template_replace(self.ans_path, 'PRIVATE', self._private)
        print('!!!            ans path: %s' % path)

    def __ans_path(self) -> str:
        path = self.ans_path
        return template_replace(path, 'PRIVATE', self._private)

    def load_records(self) -> Dict[str, ID]:
        path = self.__ans_path()
        self.info('Loading ANS records from: %s' % path)
        records = {}
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            for name in dictionary:
                value = dictionary[name]
                # convert ID
                uid = ID.parse(identifier=value)
                if uid is None:
                    self.error(msg='invalid record: %s => %s' % (name, value))
                    continue
                records[name] = uid
        #
        #  Reserved names
        #
        records['all'] = EVERYONE
        records[EVERYONE.name] = EVERYONE
        records[ANYONE.name] = ANYONE
        records['owner'] = ANYONE
        records['founder'] = FOUNDER  # 'Albert Moky'
        return records

    def save_records(self, records: Dict[str, ID]) -> bool:
        dictionary = {}
        # revert ID
        for name in records:
            uid = records[name]
            if uid is not None:
                dictionary[name] = str(uid)
        path = self.__ans_path()
        self.info('Saving %d ANS records into: %s' % (len(records), path))
        return self.write_json(container=dictionary, path=path)
