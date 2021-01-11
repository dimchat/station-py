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
from typing import Optional

from dimp import ID, Document

from .storage import Storage


class ProfileTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: dict = {}
        self.__empty = {'desc': 'just to avoid loading non-exists file again'}

    """
        Profile for Entities (User/Group)
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/mkm/{ADDRESS}/profile.js'
        file path: '.dim/public/{ADDRESS}/profile.js'
    """
    def __path(self, identifier: ID) -> str:
        return os.path.join(self.root, 'public', str(identifier.address), 'profile.js')

    def save_profile(self, profile: Document) -> bool:
        if not profile.valid:
            # raise ValueError('document not valid: %s' % profile)
            self.error('document not valid: %s' % profile)
            return False
        identifier = profile.identifier
        # 1. store into memory cache
        self.__caches[identifier] = profile
        # 2. save into local storage
        path = self.__path(identifier=identifier)
        self.info('saving document into: %s' % path)
        return self.write_json(container=profile.dictionary, path=path)

    def profile(self, identifier: ID, doc_type: str='*') -> Optional[Document]:
        # 1. try from memory cache
        info = self.__caches.get(identifier)
        if info is None:
            # 2. try from local storage
            path = self.__path(identifier=identifier)
            self.info('loading document from: %s' % path)
            dictionary = self.read_json(path=path)
            if dictionary is not None:
                data = dictionary.get('data')
                if data is None:
                    # compatible with v1.0
                    data = dictionary.get('profile')
                signature = dictionary.get('signature')
                info = Document.create(doc_type=doc_type, identifier=identifier, data=data, signature=signature)
            if info is None:
                # 2.1. place an empty meta for cache
                info = self.__empty
            # 3. store into memory cache
            self.__caches[identifier] = info
        if info is not self.__empty:
            return info
        self.error('document not found: %s' % identifier)


class DeviceTable(Storage):

    def __init__(self):
        super().__init__()
        # memory caches
        self.__caches: dict = {}
        self.__empty = {'desc': 'just to avoid loading non-exists file again'}

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
        self.info('saving device info into: %s' % path)
        return self.write_json(container=device, path=path)

    def device(self, identifier: ID) -> Optional[dict]:
        # 1. try from memory cache
        info = self.__caches.get(identifier)
        if info is None:
            # 2. try from local storage
            path = self.__path(identifier=identifier)
            self.info('loading device from: %s' % path)
            info = self.read_json(path=path)
            if info is None:
                info = self.__empty
            # 3. store into memory cache
            self.__caches[identifier] = info
        if info is not self.__empty:
            return info
        self.error('device not found: %s' % identifier)

    def save_device_token(self, token: str, identifier: ID) -> bool:
        # get device info with ID
        device = self.device(identifier=identifier)
        if device is None:
            device = {'tokens': [token]}
        else:
            # get tokens list for updating
            tokens = device.get('tokens')
            if tokens is None:
                # new device token
                tokens = [token]
            elif token in tokens:
                # already exists
                return True
            elif len(tokens) > 2:
                # keep only last three records
                tokens = tokens[-2:]
                # append token
                tokens.append(token)
            device['tokens'] = tokens
        return self.save_device(device=device, identifier=identifier)

    def device_tokens(self, identifier: ID) -> Optional[list]:
        # get device info with ID
        device = self.device(identifier=identifier)
        if device is not None:
            return device.get('tokens')
