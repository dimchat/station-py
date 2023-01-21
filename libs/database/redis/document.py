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

from dimples import utf8_encode, utf8_decode, json_encode, json_decode
from dimples import ID, Document

from ..dos.document import parse_document

from .base import Cache


class DocumentCache(Cache):

    # document cached in Redis will be removed after 10 hours, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 36000  # seconds

    @property  # Override
    def db_name(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def tbl_name(self) -> str:
        return 'document'

    """
        Document for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.document.{ID}'
    """
    def __key(self, identifier: ID) -> str:
        return '%s.%s.%s' % (self.db_name, self.tbl_name, identifier)

    def __prefix(self) -> str:
        return '%s.%s.' % (self.db_name, self.tbl_name)

    def save_document(self, document: Document) -> bool:
        identifier = document.identifier
        dictionary = document.dictionary
        js = json_encode(obj=dictionary)
        value = utf8_encode(string=js)
        name = self.__key(identifier=identifier)
        self.set(name=name, value=value, expires=self.EXPIRES)
        return True

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        name = self.__key(identifier=identifier)
        value = self.get(name=name)
        if value is None:
            return None
        js = utf8_decode(data=value)
        dictionary = json_decode(string=js)
        assert dictionary is not None, 'document error: %s' % value
        return parse_document(dictionary=dictionary, identifier=identifier, doc_type=doc_type)

    # def scan_documents(self) -> Set[ID]:
    #     """ Scan documents in Redis Server for IDs """
    #     all_ids = set()
    #     prefix = self.__prefix()
    #     pre_len = len(prefix)
    #     match = '%s*' % prefix  # 'mkm.document.*'
    #     cursor = 0
    #     while True:
    #         cursor, array = self.scan(cursor=cursor, match=match, count=1024)
    #         # fetch ID from array result
    #         for item in array:
    #             value = utf8_decode(data=item)
    #             value = value[pre_len:]
    #             identifier = ID.parse(identifier=value)
    #             if identifier is None:
    #                 print('[REDIS] document key error: %s' % item)
    #                 continue
    #             all_ids.add(identifier)
    #         if cursor == 0:
    #             # mission accomplished
    #             break
    #     return all_ids
