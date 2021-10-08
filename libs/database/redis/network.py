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

from typing import Optional

from dimp import utf8_encode, utf8_decode
from dimp import ID

from .base import Cache


class NetworkCache(Cache):

    @property  # Override
    def database(self) -> Optional[str]:
        return 'dim'

    @property  # Override
    def table(self) -> str:
        return 'network'

    """
        DIM Network
        ~~~~~~~~~~~

        redis key: 'dim.network.xxx'
    """
    def __key(self, suffix: str) -> str:
        return '%s.%s.%s' % (self.database, self.table, suffix)

    #
    #   Query meta/document
    #

    def add_meta_query(self, identifier: ID):
        key = self.__key(suffix='query.meta')
        value = utf8_encode(string=str(identifier))
        self.sadd(key, value)

    def pop_meta_query(self) -> Optional[ID]:
        name = self.__key(suffix='query.meta')
        value = self.spop(name=name)
        if value is not None:
            value = utf8_decode(data=value)
            return ID.parse(identifier=value)

    def add_document_query(self, identifier: ID):
        key = self.__key(suffix='query.document')
        value = utf8_encode(string=str(identifier))
        self.sadd(key, value)

    def pop_document_query(self) -> Optional[ID]:
        name = self.__key(suffix='query.document')
        value = self.spop(name=name)
        if value is not None:
            value = utf8_decode(data=value)
            return ID.parse(identifier=value)
