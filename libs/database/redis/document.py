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

from typing import Optional, List

from dimp import utf8_encode, utf8_decode, json_encode, json_decode
from dimp import ID, Document

from ..dos.document import parse_document

from .base import Cache


class DocumentCache(Cache):

    # document cached in Redis will be removed after 10 hours, after that
    # it will be reloaded from local storage if it's still need.
    EXPIRES = 36000  # seconds

    @property  # Override
    def database(self) -> Optional[str]:
        return 'mkm'

    @property  # Override
    def table(self) -> str:
        return 'document'

    """
        Document for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'mkm.document.{ID}'
        redis key: 'mkm.docs.keys'
    """
    def __key(self, identifier: ID) -> str:
        return '%s.%s.%s' % (self.database, self.table, identifier)

    def __docs_keys(self) -> str:
        return '%s.docs.keys' % self.database

    def save_document(self, document: Document) -> bool:
        identifier = document.identifier
        dictionary = document.dictionary
        value = json_encode(obj=dictionary)
        value = utf8_encode(string=value)
        name = self.__key(identifier=identifier)
        self.set(name=name, value=value, expires=self.EXPIRES)
        item = utf8_encode(string=str(identifier))
        self.sadd(self.__docs_keys(), item)
        return True

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        name = self.__key(identifier=identifier)
        value = self.get(name=name)
        if value is None:
            return None
        value = utf8_decode(data=value)
        dictionary = json_decode(string=value)
        assert dictionary is not None, 'document error: %s' % value
        return parse_document(dictionary=dictionary, identifier=identifier, doc_type=doc_type)

    def scan_documents(self) -> List[Document]:
        """ Get all documents from Redis Server """
        documents = []
        keys = self.smembers(name=self.__docs_keys())
        for item in keys:
            i = ID.parse(identifier=utf8_decode(data=item))
            if i is None:
                # should not happen
                continue
            doc = self.document(identifier=i)
            if doc is not None:
                documents.append(doc)
        return documents
