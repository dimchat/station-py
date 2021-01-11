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
from dimp import ID, Meta, Document, User
from dimsdk import Facebook

from libs.utils.immortals import Immortals

from .database import Database


class CommonFacebook(Facebook):

    def __init__(self):
        super().__init__()
        self.__messenger = None
        self.database: Database = None
        # built-in accounts
        #     Immortal Hulk: 'hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj'
        #     Monkey King:   'moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk'
        self.__immortals = Immortals()
        self.__local_users: List[User] = None
        self.group_assistants: List[ID] = None  # robot ID list

    @property
    def messenger(self):  # CommonMessenger
        if self.__messenger is None:
            return None
        return self.__messenger()

    @messenger.setter
    def messenger(self, value):
        self.__messenger = weakref.ref(value)

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

    #
    #   super()
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

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.database.save_meta(meta=meta, identifier=identifier)

    def save_document(self, document: Document) -> bool:
        return self.database.save_document(document=document)

    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str='M') -> bool:
        return self.database.save_private_key(key=key, identifier=identifier, key_type=key_type)

    def save_contacts(self, contacts: List[ID], identifier: ID) -> bool:
        return self.database.save_contacts(contacts=contacts, user=identifier)

    def save_members(self, members: List[ID], identifier: ID) -> bool:
        return self.database.save_members(members=members, group=identifier)

    def save_assistants(self, assistants: List[ID], identifier: ID) -> bool:
        pass

    #
    #   EntityDataSource
    #

    def meta(self, identifier: ID) -> Optional[Meta]:
        if identifier.is_broadcast:
            # broadcast ID has not meta
            return None
        info = self.database.meta(identifier=identifier)
        if info is None:
            info = self.__immortals.meta(identifier=identifier)
        if info is not None and 'key' in info:
            return info
        # query from DIM network
        messenger = self.messenger
        if messenger is not None:
            messenger.query_meta(identifier=identifier)

    EXPIRES = 3600  # profile expires (1 hour)
    EXPIRES_KEY = 'expires'

    def document(self, identifier: ID, doc_type: Optional[str]='*') -> Optional[Document]:
        info = self.database.document(identifier=identifier, doc_type=doc_type)
        if info is None:
            info = self.__immortals.document(identifier=identifier, doc_type=doc_type)
        if info is not None:
            # check expired time
            now = time.time()
            expires = info.get(self.EXPIRES_KEY)
            if expires is None:
                # set expired time
                info[self.EXPIRES_KEY] = now + self.EXPIRES
                # is empty?
                if 'data' in info:
                    return info
            elif expires > now:
                # not expired yet
                return info
            # DISCUSS: broadcast profile to every stations when user upload it
            #          no need to query other stations time by time
        # query from DIM network
        messenger = self.messenger
        if messenger is not None:
            messenger.query_profile(identifier=identifier)
        return info

    #
    #   UserDataSource
    #

    def contacts(self, identifier: ID) -> Optional[List[ID]]:
        return self.database.contacts(user=identifier)

    def private_keys_for_decryption(self, identifier: ID) -> Optional[List[DecryptKey]]:
        keys = self.database.private_keys_for_decryption(identifier=identifier)
        if keys is None or len(keys) == 0:
            keys = self.__immortals.private_keys_for_decryption(identifier=identifier)
        return keys

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        key = self.database.private_key_for_signature(identifier=identifier)
        if key is None:
            key = self.__immortals.private_key_for_signature(identifier=identifier)
        return key

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        key = self.private_key_for_signature(identifier=identifier)
        if key is None:
            key = self.__immortals.private_key_for_visa_signature(identifier=identifier)
        return key

    #
    #    GroupDataSource
    #

    def founder(self, identifier: ID) -> ID:
        # get from database
        user = self.database.founder(group=identifier)
        if user is not None:
            return user
        return super().founder(identifier=identifier)

    def owner(self, identifier: ID) -> ID:
        # get from database
        user = self.database.owner(group=identifier)
        if user is not None:
            return user
        return super().owner(identifier=identifier)

    def members(self, identifier: ID) -> Optional[List[ID]]:
        return self.database.members(group=identifier)

    def assistants(self, identifier: ID) -> Optional[List[ID]]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        # get group assistants
        robots = self.group_assistants
        if robots is not None:
            return robots
        # get from ANS
        robot = ID.parse(identifier='assistant')
        if robot is not None:
            return [robot]

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
