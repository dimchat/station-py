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

from typing import List

from dimples import DateTime
from dimples import ID, Document, DocumentHelper

from dimples.utils import CacheManager
from dimples import DocumentDBI

from .redis import DocumentCache
from .dos import DocumentStorage


class DocumentTable(DocumentDBI):
    """ Implementations of DocumentDBI """

    CACHE_EXPIRES = 300    # seconds
    CACHE_REFRESHING = 32  # seconds

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        self.__dos = DocumentStorage(root=root, public=public, private=private)
        self.__redis = DocumentCache()
        man = CacheManager()
        self.__docs_cache = man.get_pool(name='documents')  # ID => List[Document]

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
        # 0. check old documents
        my_documents = self.documents(identifier=identifier)
        old = DocumentHelper.last_document(my_documents, doc_type)
        if old is None and doc_type == Document.VISA:
            old = DocumentHelper.last_document(my_documents, 'profile')
        if old is not None:
            if DocumentHelper.is_expired(document, old):
                # self.warning(msg='drop expired document: %s' % identifier)
                return False
            my_documents.remove(old)
        my_documents.append(document)
        # update cache for Search Engine
        all_documents, _ = self.__docs_cache.fetch(key='all_documents')
        if all_documents is not None:
            assert isinstance(all_documents, List), 'all_documents error: %s' % all_documents
            all_documents.append(document)
        # 1. store into memory cache
        self.__docs_cache.update(key=identifier, value=my_documents, life_span=self.CACHE_EXPIRES)
        # 2. store into redis server
        self.__redis.save_documents(documents=my_documents, identifier=identifier)
        # 3. save into local storage
        return self.__dos.save_documents(documents=my_documents, identifier=identifier)

    # Override
    def documents(self, identifier: ID) -> List[Document]:
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__docs_cache.fetch(key=identifier, now=now)
        if value is None:
            # cache empty
            if holder is None:
                # cache not load yet, wait to load
                self.__docs_cache.update(key=identifier, life_span=self.CACHE_REFRESHING, now=now)
            else:
                if holder.is_alive(now=now):
                    # cache not exists
                    return []
                # cache expired, wait to reload
                holder.renewal(duration=self.CACHE_REFRESHING, now=now)
            # 2. check redis server
            value = self.__redis.documents(identifier=identifier)
            if value is None:
                # 3. check local storage
                value = self.__dos.documents(identifier=identifier)
                if value is not None:
                    # update redis server
                    self.__redis.save_documents(documents=value, identifier=identifier)
            # update memory cache
            self.__docs_cache.update(key=identifier, value=value, life_span=self.CACHE_EXPIRES, now=now)
        # OK, return cached value
        return value

    def scan_documents(self) -> List[Document]:
        """ Scan all documents from data directory """
        now = DateTime.now()
        # 1. check memory cache
        value, holder = self.__docs_cache.fetch(key='all_documents', now=now)
        if value is None:
            # cache empty
            if holder is None:
                # scan results not load yet, wait to load
                self.__docs_cache.update(key='all_documents', life_span=600, now=now)
            else:
                if holder.is_alive(now=now):
                    # scan results not exists
                    return []
                # scan results expired, wait to reload
                holder.renewal(duration=600, now=now)
            # 2. scan local storage
            value = self.__dos.scan_documents()
            self.__docs_cache.update(key='all_documents', value=value, life_span=3600, now=now)
        return value
