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
    Common extensions for Facebook
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Barrack for cache entities
"""

import time
import weakref
from typing import Optional, List

from dimp import PrivateKey, SignKey, DecryptKey
from dimp import ID, Meta, Document, User, Group
from dimsdk import Facebook

from ..utils import Singleton
from .database import Database


class CommonFacebook(Facebook):

    def __init__(self):
        super().__init__()
        self.__messenger: Optional[weakref.ReferenceType] = None
        self.__db = Database()
        self.__local_users: Optional[List[User]] = None
        self.__group_assistants = set()

    @property
    def messenger(self):  # -> CommonMessenger:
        if self.__messenger is not None:
            return self.__messenger()

    @messenger.setter
    def messenger(self, transceiver):
        if transceiver is None:
            self.__messenger = None
        else:
            self.__messenger = weakref.ref(transceiver)

    #
    #   Local Users
    #

    @property
    def local_users(self) -> Optional[List[User]]:
        return self.__local_users

    @local_users.setter
    def local_users(self, value: List[User]):
        self.__local_users = value

    @property
    def current_user(self) -> Optional[User]:
        users = self.local_users
        if users is not None and len(users) > 0:
            return users[0]

    @current_user.setter
    def current_user(self, user: User):
        if user is None:
            raise ValueError('current user cannot be empty')
        array = self.local_users
        if array is None:
            array = []
        elif user in array:
            array.remove(user)
        array.insert(0, user)
        self.__local_users = array

    #
    #   Contacts
    #

    def save_contacts(self, contacts: List[ID], identifier: ID) -> bool:
        return self.__db.save_contacts(contacts=contacts, user=identifier)

    #
    #   Private Keys
    #

    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M') -> bool:
        return self.__db.save_private_key(key=key, identifier=identifier, key_type=key_type)

    #
    #   Meta
    #

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.__db.save_meta(meta=meta, identifier=identifier)

    #
    #   Document
    #

    def save_document(self, document: Document) -> bool:
        meta = self.meta(identifier=document.identifier)
        if meta is None or not document.verify(public_key=meta.key):
            return False
        return self.__db.save_document(document=document)

    EXPIRES = 3600  # profile expires (1 hour)
    EXPIRES_KEY = 'expires'

    def is_expired_document(self, document: Document, reset: bool = True) -> bool:
        # check expired time
        now = time.time()
        expires = document.get(self.EXPIRES_KEY)
        if expires is None:
            # set expired time
            document[self.EXPIRES_KEY] = now + self.EXPIRES
            return False
        if now > expires:
            if reset:
                # update expired time
                document[self.EXPIRES_KEY] = now + self.EXPIRES
            return True

    #
    #   Relationship
    #

    def save_members(self, members: List[ID], identifier: ID) -> bool:
        return self.__db.save_members(members=members, group=identifier)

    def save_assistants(self, assistants: List[ID], identifier: ID) -> bool:
        pass

    def exists_member(self, member: ID, group: ID) -> bool:
        members = self.members(identifier=group)
        if members is not None and member in members:
            return True
        owner = self.owner(identifier=group)
        return owner == member

    def exists_assistant(self, member: ID, group: ID) -> bool:
        assistants = self.assistants(identifier=group)
        if assistants is not None and member in assistants:
            return True

    def name(self, identifier: ID) -> str:
        profile = self.document(identifier=identifier)
        if profile is not None:
            name = profile.name
            if name is not None and len(name) > 0:
                return name
        name = identifier.name
        if name is not None and len(name) > 0:
            return name
        return str(identifier.address)

    def __waiting_meta(self, identifier: ID) -> bool:
        if identifier.is_broadcast:
            return False
        return self.meta(identifier=identifier) is None

    def create_user(self, identifier: ID) -> Optional[User]:
        if not self.__waiting_meta(identifier=identifier):
            return super().create_user(identifier=identifier)

    def create_group(self, identifier: ID) -> Optional[Group]:
        if not self.__waiting_meta(identifier=identifier):
            return super().create_group(identifier=identifier)

    #
    #   EntityDataSource
    #

    def meta(self, identifier: ID) -> Optional[Meta]:
        if identifier.is_broadcast:
            # broadcast ID has no meta
            return None
        # try from database
        info = self.__db.meta(identifier=identifier)
        if info is None:
            # query from DIM network
            messenger = self.messenger
            if messenger is not None:
                messenger.query_meta(identifier=identifier)
        return info

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        if identifier.is_broadcast:
            # broadcast ID has no document
            return None
        # try from database
        info = self.__db.document(identifier=identifier, doc_type=doc_type)
        if info is None or self.is_expired_document(document=info):
            # query from DIM network
            messenger = self.messenger
            if messenger is not None:
                messenger.query_document(identifier=identifier)
        return info

    #
    #   UserDataSource
    #

    def contacts(self, identifier: ID) -> Optional[List[ID]]:
        return self.__db.contacts(user=identifier)

    def private_keys_for_decryption(self, identifier: ID) -> Optional[List[DecryptKey]]:
        return self.__db.private_keys_for_decryption(identifier=identifier)

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__db.private_key_for_signature(identifier=identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__db.private_key_for_visa_signature(identifier=identifier)

    #
    #    GroupDataSource
    #

    def founder(self, identifier: ID) -> ID:
        # get from database
        user = self.__db.founder(group=identifier)
        if user is not None:
            return user
        return super().founder(identifier=identifier)

    def owner(self, identifier: ID) -> ID:
        # get from database
        user = self.__db.owner(group=identifier)
        if user is not None:
            return user
        return super().owner(identifier=identifier)

    def members(self, identifier: ID) -> Optional[List[ID]]:
        array = self.__db.members(group=identifier)
        if array is not None and len(array) > 0:
            return array
        return super().members(identifier=identifier)

    def assistants(self, identifier: ID) -> Optional[List[ID]]:
        array = super().assistants(identifier=identifier)
        if array is not None and len(array) > 0:
            return array
        # get from global setting
        if len(self.__group_assistants) > 0:
            return list(self.__group_assistants)
        # get from ANS
        robot = ID.parse(identifier='assistant')
        if robot is not None:
            return [robot]

    def add_assistant(self, assistant: ID):
        self.__group_assistants.add(assistant)


@Singleton
class SharedFacebook(CommonFacebook):
    pass
