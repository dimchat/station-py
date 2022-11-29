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

from dimp import ID, Document

from .base import Storage


class DocumentStorage(Storage):
    """
        Document for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/mkm/{ADDRESS}/profile.js'
        file path: '.dim/public/{ADDRESS}/profile.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'profile.js')

    def save_document(self, document: Document) -> bool:
        identifier = document.identifier
        dictionary = document.dictionary
        path = self.__path(identifier=identifier)
        self.info('Saving document into: %s' % path)
        return self.write_json(container=dictionary, path=path)

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        path = self.__path(identifier=identifier)
        self.info('Loading document from: %s' % path)
        dictionary = self.read_json(path=path)
        return parse_document(dictionary=dictionary, identifier=identifier, doc_type=doc_type)

    def scan_documents(self) -> List[Document]:
        """ Scan all documents from data directory """
        documents = []
        directory = os.path.join(self.root, 'public')
        array = os.listdir(directory)
        for item in array:
            path = os.path.join(directory, item, 'profile.js')
            self.info('Loading document from: %s' % path)
            dictionary = self.read_json(path=path)
            doc = parse_document(dictionary=dictionary)
            if doc is not None:
                documents.append(doc)
        self.debug('Scanned %d documents(s) from %s' % (len(documents), directory))
        return documents


def parse_document(dictionary: Optional[dict],
                   identifier: Optional[ID] = None,
                   doc_type: Optional[str] = '*') -> Optional[Document]:
    if dictionary is None:
        return None
    if identifier is None:
        identifier = ID.parse(identifier=dictionary.get('ID'))
        if identifier is None:
            raise ValueError('document error: %s' % dictionary)
    dt = dictionary.get('type')
    if dt is not None:
        doc_type = dt
    data = dictionary.get('data')
    if data is None:
        # compatible with v1.0
        data = dictionary.get('profile')
    signature = dictionary.get('signature')
    if data is None or signature is None:
        raise ValueError('document error: %s' % dictionary)
    return Document.create(doc_type=doc_type, identifier=identifier, data=data, signature=signature)
