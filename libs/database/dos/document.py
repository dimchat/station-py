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
from typing import Optional, Union, List

from dimp import ID, Document

from dimples.utils import Log
from dimples.database.dos.base import template_replace
from dimples.database.dos.document import parse_document
from dimples.database import DocumentStorage as SuperStorage


class DocumentStorage(SuperStorage):

    # compatible with v1.0
    doc_path_old = '{PUBLIC}/{ADDRESS}/profile.js'
    doc_path_new = '{PUBLIC}/{ADDRESS}/document.js'

    def __path(self, address: Union[ID, str], path: str) -> str:
        if isinstance(address, ID):
            address = str(address.address)
        path = template_replace(path, 'PUBLIC', self._public)
        return template_replace(path, 'ADDRESS', address)

    def __doc_path_old(self, address: Union[ID, str]) -> str:
        return self.__path(address=address, path=self.doc_path_old)

    def __doc_path_new(self, address: Union[ID, str]) -> str:
        return self.__path(address=address, path=self.doc_path_new)

    # Override
    def document(self, identifier: ID, doc_type: str = '*') -> Optional[Document]:
        """ load document from file """
        return load_document(address=str(identifier.address), pub=self._public)

    def scan_documents(self) -> List[Document]:
        """ Scan documents from local directory for IDs """
        documents = []
        pub = self._public
        array = os.listdir(pub)
        for item in array:
            doc = load_document(address=item, pub=pub)
            if doc is not None:
                documents.append(doc)
        self.debug('Scanned %d documents(s) from %s' % (len(documents), pub))
        return documents


def load_document(address: str, pub: str) -> Optional[Document]:
    path = get_path(address=address, pub=pub, path=DocumentStorage.doc_path_new)
    if not os.path.exists(path):
        # load from old version
        path = get_path(address=address, pub=pub, path=DocumentStorage.doc_path_old)
    Log.info(msg='Loading document from: %s' % path)
    info = DocumentStorage.read_json(path=path)
    if info is not None:
        return parse_document(dictionary=info)


def get_path(address: str, pub: str, path: str) -> str:
    path = template_replace(path, 'PUBLIC', pub)
    return template_replace(path, 'ADDRESS', address)
