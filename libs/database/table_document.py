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

from typing import Optional, List, Dict

from dimp import ID, Document

from .redis import DocumentCache
from .dos import DocumentStorage

from .cache import CacheHolder, CachePool


class DocumentTable:

    def __init__(self):
        super().__init__()
        self.__redis = DocumentCache()
        self.__dos = DocumentStorage()
        # memory caches
        self.__caches: Dict[ID, CacheHolder[Document]] = CachePool.get_caches('document')
        self.__scanned: Optional[CacheHolder] = None

    def save_document(self, document: Document) -> bool:
        # 0. check document valid
        if not document.valid:
            # raise ValueError('document not valid: %s' % document)
            return False
        identifier = document.identifier
        # check old record with time
        old = self.document(identifier=identifier)
        if old is not None and old.time > document.time > 0:
            # document expired, drop it
            return False
        # 1. store into memory cache
        self.__caches[identifier] = CacheHolder(value=document)
        # 2. store into redis server
        self.__redis.save_document(document=document)
        # 3. save into local storage
        return self.__dos.save_document(document=document)

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        # 1. check memory cache
        holder = self.__caches.get(identifier)
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__caches[identifier] = CacheHolder(life_span=128)
            else:
                holder.renewal()
            # 2. check redis server
            doc = self.__redis.document(identifier=identifier, doc_type=doc_type)
            if doc is None:
                # 3. check local storage
                doc = self.__dos.document(identifier=identifier, doc_type=doc_type)
                if doc is not None:
                    # update redis server
                    self.__redis.save_document(document=doc)
            # update memory cache
            holder = CacheHolder(value=doc)
            self.__caches[identifier] = holder
        # OK, return cached value
        return holder.value

    def scan_documents(self) -> List[Document]:
        """ Scan all documents from data directory """
        holder = self.__scanned
        if holder is None or not holder.alive:
            # renewal or place an empty holder to avoid frequent reading
            if holder is None:
                self.__scanned = CacheHolder(value=[])
            else:
                holder.renewal(duration=3600)
            # scan from local storage
            documents = self.__dos.scan_documents()
            # update memory cache
            holder = CacheHolder(value=documents)
            self.__scanned = holder
        # OK, return cached value
        return holder.value
