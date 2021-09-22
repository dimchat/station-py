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

import json
import os
from typing import Optional, List, Dict

from dimp import ID, Document

from .storage import Storage


def parse_info(dictionary: dict, identifier: Optional[ID], doc_type: Optional[str] = '*') -> Optional[Document]:
    dt = dictionary.get('type')
    if dt is not None:
        doc_type = dt
    data = dictionary.get('data')
    if data is None:
        # compatible with v1.0
        data = dictionary.get('profile')
    signature = dictionary.get('signature')
    assert identifier is not None and data is not None and signature is not None,\
        'doc error: %s -> %s' % (identifier, dictionary)
    return Document.create(doc_type=doc_type, identifier=identifier, data=data, signature=signature)


class DocumentTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: Dict[ID, Document] = {}
        self.__empty = {'desc': 'just to avoid loading non-exists file again'}
        self.__scanned = False

    """
        Profile for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/mkm/{ADDRESS}/profile.js'
        file path: '.dim/public/{ADDRESS}/profile.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'profile.js')

    def __save_json(self, identifier: ID, dictionary: dict) -> bool:
        path = self.__path(identifier=identifier)
        self.info('Saving document into: %s' % path)
        return self.write_json(container=dictionary, path=path)

    def __load_json(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        path = self.__path(identifier=identifier)
        self.info('Loading document from: %s' % path)
        dictionary = self.read_json(path=path)
        if dictionary is not None:
            return parse_info(dictionary=dictionary, identifier=identifier, doc_type=doc_type)

    def __scan_json(self) -> List[Document]:
        documents = []
        directory = os.path.join(self.root, 'public')
        array = os.listdir(directory)
        for item in array:
            path = os.path.join(directory, item, 'profile.js')
            self.info('Loading document from: %s' % path)
            dictionary = self.read_json(path=path)
            if dictionary is None:
                self.error('document not exists: %s' % item)
                continue
            identifier = ID.parse(identifier=dictionary.get('ID'))
            if identifier is None:
                self.error('document error: %s' % dictionary)
                continue
            doc = parse_info(dictionary=dictionary, identifier=identifier)
            if doc is not None:
                documents.append(doc)
        self.debug('Scanned %d documents(s) from %s' % (len(documents), directory))
        return documents

    def __save_redis(self, identifier: ID, dictionary: dict):
        info = json.dumps(dictionary)
        self.redis.hset(name='mkm.documents', key=str(identifier), value=info)

    def __load_redis(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document, dict]:
        info = self.redis.hget(name='mkm.documents', key=str(identifier))
        if info is None:
            return None
        dictionary = json.loads(info)
        if dictionary is None:
            return self.__empty
        if 'ID' not in dictionary:
            return self.__empty
        if 'data' not in dictionary and 'profile' not in dictionary:
            return self.__empty
        if 'signature' not in dictionary:
            return self.__empty
        # OK
        return parse_info(dictionary=dictionary, identifier=identifier, doc_type=doc_type)

    def __scan_redis(self) -> List[Document]:
        documents = []
        keys = self.redis.hkeys(name='mkm.documents')
        for item in keys:
            i = ID.parse(identifier=item)
            if i is None:
                # should not happen
                continue
            doc = self.document(identifier=i)
            if doc is not None:
                documents.append(doc)
        return documents

    def save_document(self, document: Document) -> bool:
        if not document.valid:
            # raise ValueError('document not valid: %s' % profile)
            self.error('document not valid: %s' % document)
            return False
        identifier = document.identifier
        # 0. check old record
        old = self.document(identifier=identifier)
        if old is not None and old.time > document.time > 0:
            self.warning('document expired, drop it: %s' % document)
            return False
        # 1. store into memory cache
        self.__caches[identifier] = document
        # 2. store into redis server
        dictionary = document.dictionary
        self.__save_redis(identifier=identifier, dictionary=dictionary)
        # 3. save into local storage
        return self.__save_json(identifier=identifier, dictionary=dictionary)

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        # 1. try from memory cache
        doc = self.__caches.get(identifier)
        if doc is not None:
            # got from memory cache
            return doc
        # 2. try from redis server
        doc = self.__load_redis(identifier=identifier, doc_type=doc_type)
        if doc is not None and doc is not self.__empty:
            # got from redis server, store it into memory cache now
            self.__caches[identifier] = doc
            return doc
        # 3. try from local storage
        doc = self.__load_json(identifier=identifier, doc_type=doc_type)
        if doc is not None:
            # got from local storage, store it into redis server & memory cache
            self.__save_redis(identifier=identifier, dictionary=doc.dictionary)
            self.__caches[identifier] = doc
            return doc
        else:
            # file not found. place an empty meta for cache
            self.__save_redis(identifier=identifier, dictionary=self.__empty)
            self.info('document not found: %s' % identifier)

    def scan_documents(self) -> List[Document]:
        """ Scan all documents from data directory """
        if self.__scanned:
            # already scanned from local storage and stored into redis server
            return self.__scan_redis()
        documents = self.__scan_json()
        # got all documents from local storage, store them into redis server & memory cache
        for doc in documents:
            identifier = doc.identifier
            if identifier is None:
                self.error('document error: %s' % doc)
                continue
            self.__save_redis(identifier=identifier, dictionary=doc.dictionary)
            self.__caches[identifier] = doc
        # OK
        self.__scanned = True


class DeviceTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: Dict[ID, dict] = {}

    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/device.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'protected', str(identifier.address), 'device.js')

    def save_device(self, device: dict, identifier: ID) -> bool:
        # 1. store info memory cache
        self.__caches[identifier] = device
        # 2. save into local storage
        path = self.__path(identifier=identifier)
        self.info('Saving device info into: %s' % path)
        return self.write_json(container=device, path=path)

    def device(self, identifier: ID) -> Optional[dict]:
        # 1. try from memory cache
        info = self.__caches.get(identifier)
        if info is None:
            # 2. try from local storage
            path = self.__path(identifier=identifier)
            self.info('Loading device from: %s' % path)
            info = self.read_json(path=path)
            if info is None:
                self.info('device not found: %s' % identifier)
                info = {}
            # 3. store into memory cache
            self.__caches[identifier] = info
        return info

    def save_device_token(self, token: str, identifier: ID) -> bool:
        # get device info with ID
        device = self.device(identifier=identifier)
        if device is None:
            device = {'tokens': [token]}
        else:
            # get tokens list for updating
            tokens: list = device.get('tokens')
            if tokens is None:
                # new device token
                tokens = [token]
            elif token in tokens:
                # already exists
                return True
            else:
                # keep only last three records
                while len(tokens) > 2:
                    tokens.pop()
                tokens.insert(0, token)
            device['tokens'] = tokens
        return self.save_device(device=device, identifier=identifier)

    def device_tokens(self, identifier: ID) -> Optional[List[str]]:
        # get device info with ID
        device = self.device(identifier=identifier)
        if device is not None:
            return device.get('tokens')
