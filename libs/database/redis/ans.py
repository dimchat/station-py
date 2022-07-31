# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

from typing import Optional, Set

from dimsdk import utf8_encode, utf8_decode
from dimsdk import ID

from .base import Cache


class AddressNameCache(Cache):

    @property  # Override
    def database(self) -> Optional[str]:
        return 'dim'

    @property  # Override
    def table(self) -> str:
        return 'ans'

    """
        Address Name Service
        ~~~~~~~~~~~~~~~~~~~~

        redis key: 'dim.ans'
    """
    def __key(self) -> str:
        return '%s.%s' % (self.database, self.table)

    def save_record(self, name: str, identifier: ID):
        value = utf8_encode(string=str(identifier))
        self.hset(name=self.__key(), key=name, value=value)
        return True

    def record(self, name: str) -> Optional[ID]:
        value = self.hget(name=self.__key(), key=name)
        if value is not None:
            return ID.parse(identifier=utf8_decode(data=value))

    def names(self, identifier: ID) -> Set[str]:
        strings = set()
        dictionary = self.hgetall(name=self.__key())
        if dictionary is not None:
            for key in dictionary:
                if identifier == dictionary[key]:
                    strings.add(key)
        return strings
