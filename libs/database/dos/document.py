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
from typing import Optional, List

from dimples import ID, Document

from dimples.utils import Log, Path
from dimples.database.dos.base import template_replace
from dimples.database.dos.document import parse_document
from dimples.database import DocumentStorage as SuperStorage


class DocumentStorage(SuperStorage):

    # compatible with v1.0
    doc_path_old = '{PUBLIC}/{ADDRESS}/profile.js'
    doc_path_new = '{PUBLIC}/{ADDRESS}/document.js'
    doc_path_all = '{PUBLIC}/{ADDRESS}/documents.js'

    # def __path(self, address: Union[ID, str], path: str) -> str:
    #     if isinstance(address, ID):
    #         address = str(address.address)
    #     path = self.public_path(path)
    #     return template_replace(path, 'ADDRESS', address)

    def __doc_path_old(self, identifier: ID) -> str:
        path = self.public_path(self.doc_path_old)
        return template_replace(path, key='ADDRESS', value=str(identifier.address))

    def __doc_path_new(self, identifier: ID) -> str:
        path = self.public_path(self.doc_path_new)
        return template_replace(path, key='ADDRESS', value=str(identifier.address))

    # Override
    async def load_documents(self, identifier: ID) -> List[Document]:
        """ load documents from file """
        all_documents = await super().load_documents(identifier=identifier)
        if all_documents is not None:
            return all_documents
        # try old file
        doc = await self.load_document(identifier=identifier)
        return [] if doc is None else [doc]

    async def load_document(self, identifier: ID) -> Optional[Document]:
        """ load document from file """
        path = self.__doc_path_new(identifier=identifier)
        if not await Path.exists(path=path):
            # load from old version
            path = self.__doc_path_old(identifier=identifier)
        self.info(msg='Loading document from: %s' % path)
        info = await self.read_json(path=path)
        if info is not None:
            return parse_document(dictionary=info, identifier=identifier)

    async def scan_documents(self) -> List[Document]:
        """ Scan documents from local directory for IDs """
        documents = []
        pub = self.public_dir
        array = os.listdir(pub)
        for item in array:
            docs = await load_documents(address=item, pub=pub)
            if docs is None:  # or len(docs) == 0:
                # try to load from old files
                doc = await load_document(address=item, pub=pub)
                if doc is not None:
                    documents.append(doc)
            else:
                for doc in docs:
                    documents.append(doc)
        self.info(msg='Scanned %d documents(s) from %s' % (len(documents), pub))
        return documents


async def load_documents(address: str, pub: str) -> Optional[List[Document]]:
    path = get_path(address=address, pub=pub, path=DocumentStorage.doc_path_all)
    Log.info(msg='Loading document from: %s' % path)
    array = await DocumentStorage.read_json(path=path)
    if array is None:
        return None
    documents = []
    for info in array:
        doc = parse_document(dictionary=info)
        if doc is None:
            Log.error(msg='document error: %s' % info)
        else:
            documents.append(doc)
    return documents


async def load_document(address: str, pub: str) -> Optional[Document]:
    path = get_path(address=address, pub=pub, path=DocumentStorage.doc_path_new)
    if not await Path.exists(path=path):
        # load from old version
        path = get_path(address=address, pub=pub, path=DocumentStorage.doc_path_old)
    Log.info(msg='Loading document from: %s' % path)
    info = await DocumentStorage.read_json(path=path)
    if info is not None:
        return parse_document(dictionary=info)


def get_path(address: str, pub: str, path: str) -> str:
    path = template_replace(path, 'PUBLIC', pub)
    return template_replace(path, 'ADDRESS', address)
