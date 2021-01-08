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

"""
    Immortals
    ~~~~~~~~~

    Built-in users
"""

import os
from typing import Optional

from dimp import PrivateKey, EncryptKey, DecryptKey, SignKey, VerifyKey
from dimp import Meta, Document, Visa
from dimp import ID, User, UserDataSource

from .dos import JSONFile


def load_resource_file(filename: str) -> dict:
    directory = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(directory, 'res', filename)
    file = JSONFile(path=path)
    return file.read()


class Immortals(UserDataSource):

    # Immortal Hulk (195-183-9394)
    HULK = 'hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj'
    # Monkey King (184-083-9527)
    MOKI = 'moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk'

    def __init__(self):
        super().__init__()
        # caches
        self.__ids = {}
        self.__private_keys = {}
        self.__metas = {}
        self.__profiles = {}
        self.__users = {}
        # load built-in users
        self.__load_user(identifier=ID.parse(self.HULK))
        self.__load_user(identifier=ID.parse(self.MOKI))

    def __load_user(self, identifier: ID):
        self.__ids[identifier] = identifier
        # load meta for ID
        meta = self.__load_meta(filename=identifier.name+'_meta.js')
        self.cache_meta(meta=meta, identifier=identifier)
        # load private key for ID
        key = self.__load_private_key(filename=identifier.name+'_secret.js')
        self.cache_private_key(private_key=key, identifier=identifier)
        # load profile for ID
        profile = self.__load_profile(filename=identifier.name + '_profile.js')
        self.cache_profile(profile=profile, identifier=identifier)

    @staticmethod
    def __load_meta(filename: str) -> Optional[Meta]:
        return Meta.parse(meta=load_resource_file(filename=filename))

    @staticmethod
    def __load_private_key(filename: str) -> Optional[PrivateKey]:
        return PrivateKey.parse(key=load_resource_file(filename=filename))

    def __load_profile(self, filename: str) -> Optional[Document]:
        profile = Document.parse(document=load_resource_file(filename=filename))
        assert profile is not None, 'failed to load profile: %s' % filename
        # copy 'name'
        name = profile.get('name')
        if name is None:
            names = profile.get('names')
            if names is not None and len(names) > 0:
                profile.set_property('name', names[0])
        else:
            profile.set_property('name', name)
        # copy 'avatar'
        avatar = profile.get('avatar')
        if avatar is None:
            photos = profile.get('photos')
            if photos is not None and len(photos) > 0:
                profile.set_property('avatar', photos[0])
        else:
            profile.set_property('avatar', avatar)
        # sign
        self.__sign_profile(profile=profile)
        return profile

    def __sign_profile(self, profile: Document) -> bytes:
        identifier = profile.identifier
        key = self.private_key_for_signature(identifier)
        if key is not None:
            return profile.sign(private_key=key)

    def cache_meta(self, meta: Meta, identifier: ID) -> bool:
        if meta.match_identifier(identifier):
            self.__metas[identifier] = meta
            return True

    def cache_private_key(self, private_key: PrivateKey, identifier: ID) -> bool:
        self.__private_keys[identifier] = private_key
        return True

    def cache_profile(self, profile: Document, identifier: ID) -> bool:
        assert profile.valid, 'profile not valid: %s' % profile
        assert identifier == profile.identifier, 'profile not match: %s, %s' % (identifier, profile)
        self.__profiles[profile.identifier] = profile
        return True

    def cache_user(self, user: User) -> bool:
        if user.delegate is None:
            user.delegate = self
        self.__users[user.identifier] = user
        return True

    # ----

    def user(self, identifier: ID) -> Optional[User]:
        user = self.__users.get(identifier)
        if user is None:
            # only create exists account
            if identifier in self.__ids:
                user = User(identifier=identifier)
                self.cache_user(user=user)
        return user

    #
    #   EntityDataSource
    #
    def meta(self, identifier: ID) -> Optional[Meta]:
        return self.__metas.get(identifier)

    def document(self, identifier: ID, doc_type: Optional[str]='*') -> Optional[Document]:
        return self.__profiles.get(identifier)

    #
    #   UserDataSource
    #
    def contacts(self, identifier: ID) -> Optional[list]:
        if identifier not in self.__ids:
            return None
        array = []
        for key, value in self.__ids.items():
            if key == identifier:
                continue
            array.append(value)
        return array

    def __visa_key(self, identifier: ID) -> Optional[EncryptKey]:
        visa = self.document(identifier=identifier, doc_type=Document.VISA)
        if isinstance(visa, Visa):
            if visa.valid:
                return visa.key

    def __meta_key(self, identifier: ID) -> Optional[VerifyKey]:
        meta = self.meta(identifier=identifier)
        if meta is not None:
            return meta.key

    def public_key_for_encryption(self, identifier: ID) -> Optional[EncryptKey]:
        # 1. get key from visa
        key = self.__visa_key(identifier=identifier)
        if key is not None:
            # if visa.key exists, use it for encryption
            return key
        # 2. get key from meta
        key = self.__meta_key(identifier=identifier)
        if isinstance(key, EncryptKey):
            # if profile.key not exists and meta.key is encrypt key,
            # use it for encryption
            return key

    def public_keys_for_verification(self, identifier: ID) -> Optional[list]:
        keys = []
        # 1. get key from visa
        key = self.__visa_key(identifier=identifier)
        if isinstance(key, VerifyKey):
            # the sender may use communication key to sign message.data,
            # so try to verify it with visa.key here
            keys.append(key)
        # 2. get key from meta
        key = self.__meta_key(identifier=identifier)
        if key is not None:
            # the sender may use identity key to sign message.data,
            # try to verify it with meta.key
            keys.append(key)
        assert len(keys) > 0, 'failed to get verify key for user: %s' % identifier
        return keys

    def private_keys_for_decryption(self, identifier: ID) -> Optional[list]:
        key = self.__private_keys.get(identifier)
        if isinstance(key, DecryptKey):
            return [key]

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__private_keys.get(identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__private_keys.get(identifier)
