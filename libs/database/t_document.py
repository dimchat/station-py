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

import time
from typing import Optional, List

from dimples import ID, Document

from dimples.utils import CacheManager
from dimples.common import DocumentDBI

from .redis import DocumentCache
from .dos import DocumentStorage


class DocumentTable(DocumentDBI):
    """ Implementations of DocumentDBI """

    CACHE_EXPIRES = 60    # seconds
    CACHE_REFRESHING = 8  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = DocumentStorage(root=root, public=public, private=private)
        self.__redis = DocumentCache()
        man = CacheManager()
        self.__cache = man.get_pool(name='document')  # ID => Document

    def show_info(self):
        self.__dos.show_info()

    #
    #   Document DBI
    #

    # Override
    def save_document(self, document: Document) -> bool:
        assert document.valid, 'document invalid: %s' % document
        identifier = document.identifier
        doc_type = document.type
        # 0. check old record with time
        old = self.document(identifier=identifier, doc_type=doc_type)
        if old is not None and old.time >= document.time > 0:
            # document expired, drop it
            return False
        # 1. store into memory cache
        self.__cache.update(key=identifier, value=document, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_document(document=document)
        # 3. save into local storage
        return self.__dos.save_document(document=document)

    # Override
    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # document not load yet, wait to load
                self.__cache.update(key=identifier, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # document not exists
                    return None
                # document expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.document(identifier=identifier, doc_type=doc_type)
            if value is None:
                # 3. check local storage
                value = self.__dos.document(identifier=identifier, doc_type=doc_type)
                if value is not None:
                    # update redis server
                    self.__redis.save_document(document=value)
            # update memory cache
            self.__cache.update(key=identifier, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    def scan_documents(self) -> List[Document]:
        """ Scan all documents from data directory """
        now = time.time()
        # 1. check memory cache
        value, holder = self.__cache.fetch(key='all_documents', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # scan results not load yet, wait to load
                self.__cache.update(key='all_documents', life_span=128, now=now)
            else:
                if holder.is_alive(now=now):
                    # scan results not exists
                    return []
                # scan results expired, wait to reload
                holder.renewal(duration=128, now=now)
            # 2. scan local storage
            value = self.__dos.scan_documents()
            self.__cache.update(key='all_documents', value=value, life_span=600, now=now)
        return value
