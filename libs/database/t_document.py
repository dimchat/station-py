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

import threading
from typing import Optional, List

from aiou.mem import CachePool

from dimples import ID, Document, DocumentUtils
from dimples import DocumentDBI
from dimples.utils import SharedCacheManager
from dimples.database import DbInfo, DbTask

from .redis import DocumentCache
from .dos import DocumentStorage


class DocTask(DbTask):

    MEM_CACHE_EXPIRES = 300  # seconds
    MEM_CACHE_REFRESH = 32   # seconds

    def __init__(self, identifier: ID,
                 cache_pool: CachePool, redis: DocumentCache, storage: DocumentStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._identifier = identifier
        self._redis = redis
        self._dos = storage

    # Override
    def cache_key(self) -> ID:
        return self._identifier

    # Override
    async def _load_redis_cache(self) -> Optional[List[Document]]:
        docs = await self._redis.get_documents(identifier=self._identifier)
        if docs is None or len(docs) == 0:
            return None
        else:
            return docs

    # Override
    async def _save_redis_cache(self, value: List[Document]) -> bool:
        return await self._redis.save_documents(documents=value, identifier=self._identifier)

    # Override
    async def _load_local_storage(self) -> Optional[List[Document]]:
        docs = await self._dos.get_documents(identifier=self._identifier)
        if docs is None or len(docs) == 0:
            return None
        else:
            return docs

    # Override
    async def _save_local_storage(self, value: List[Document]) -> bool:
        return await self._dos.save_documents(documents=value, identifier=self._identifier)


class ScanTask(DbTask):

    ALL_KEY = 'all_documents'

    MEM_CACHE_EXPIRES = 3600  # seconds
    MEM_CACHE_REFRESH = 600   # seconds

    def __init__(self,
                 cache_pool: CachePool, storage: DocumentStorage,
                 mutex_lock: threading.Lock):
        super().__init__(cache_pool=cache_pool,
                         cache_expires=self.MEM_CACHE_EXPIRES,
                         cache_refresh=self.MEM_CACHE_REFRESH,
                         mutex_lock=mutex_lock)
        self._dos = storage

    # Override
    def cache_key(self) -> str:
        return self.ALL_KEY

    # Override
    async def _load_redis_cache(self) -> Optional[List[Document]]:
        pass

    # Override
    async def _save_redis_cache(self, value: List[Document]) -> bool:
        pass

    # Override
    async def _load_local_storage(self) -> Optional[List[Document]]:
        return await self._dos.scan_documents()

    # Override
    async def _save_local_storage(self, value: List[Document]) -> bool:
        pass


class DocumentTable(DocumentDBI):
    """ Implementations of DocumentDBI """

    def __init__(self, info: DbInfo):
        super().__init__()
        man = SharedCacheManager()
        self._cache = man.get_pool(name='documents')  # ID => List[Document]
        self._redis = DocumentCache(connector=info.redis_connector)
        self._dos = DocumentStorage(root=info.root_dir, public=info.public_dir, private=info.private_dir)
        self._lock = threading.Lock()

    def show_info(self):
        self._dos.show_info()

    def _new_doc_task(self, identifier: ID) -> DocTask:
        return DocTask(identifier=identifier,
                       cache_pool=self._cache, redis=self._redis, storage=self._dos,
                       mutex_lock=self._lock)

    def _new_scan_task(self) -> ScanTask:
        return ScanTask(cache_pool=self._cache, storage=self._dos,
                        mutex_lock=self._lock)

    #
    #   Document DBI
    #

    # Override
    async def save_document(self, document: Document) -> bool:
        assert document.valid, 'document invalid: %s' % document
        identifier = document.identifier
        doc_type = document.type
        #
        #  check old documents
        #
        my_documents = await self.get_documents(identifier=identifier)
        old = DocumentUtils.last_document(my_documents, doc_type)
        if old is None and doc_type == Document.VISA:
            old = DocumentUtils.last_document(my_documents, 'profile')
        if old is not None:
            if DocumentUtils.is_expired(document, old):
                # self.warning(msg='drop expired document: %s' % identifier)
                return False
            my_documents.remove(old)
        my_documents.append(document)
        # update cache for Search Engine
        with self._lock:
            all_documents, _ = self._cache.fetch(key=ScanTask.ALL_KEY)
            if all_documents is not None:
                assert isinstance(all_documents, List), 'all_documents error: %s' % all_documents
                all_documents.append(document)
        #
        #  build task for saving
        #
        task = self._new_doc_task(identifier=identifier)
        return await task.save(value=my_documents)

    # Override
    async def get_documents(self, identifier: ID) -> List[Document]:
        #
        #  build task for loading
        #
        task = self._new_doc_task(identifier=identifier)
        docs = await task.load()
        return [] if docs is None else docs

    async def scan_documents(self) -> List[Document]:
        """ Scan all documents from data directory """
        task = self._new_scan_task()
        docs = await task.load()
        return [] if docs is None else docs
