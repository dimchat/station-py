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
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""

from typing import Optional

from mkm.immortals import Immortals

from dimp import PrivateKey
from dimp import ID, Meta, Profile, User
from dimsdk import Facebook as Barrack

from .database import Database


class Facebook(Barrack):

    def __new__(cls, *args, **kwargs):
        """ Singleton """
        if not hasattr(cls, '_instance'):
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.database: Database = None
        # built-in accounts
        #     Immortal Hulk: 'hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj'
        #     Monkey King:   'moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk'
        self.__immortals = Immortals()
        self.__local_users = None

    def nickname(self, identifier: ID) -> str:
        assert identifier.type.is_user(), 'user ID error: %s' % identifier
        profile = self.profile(identifier=identifier)
        if profile is not None:
            name = profile.name
            if name is not None and len(name) > 0:
                return name
        return identifier.name

    def group_name(self, identifier: ID) -> str:
        assert identifier.type.is_group(), 'group ID error: %s' % identifier
        profile = self.profile(identifier=identifier)
        if profile is not None:
            name = profile.name
            if name is not None and len(name) > 0:
                return name
        return identifier.name

    #
    #   super()
    #
    @property
    def local_users(self) -> Optional[list]:
        return self.__local_users

    @local_users.setter
    def local_users(self, value: list):
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
        self.local_users = array

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        if not self.verify_meta(meta=meta, identifier=identifier):
            raise ValueError('meta error: %s, %s' % (identifier, meta))
        return self.database.save_meta(meta=meta, identifier=identifier)

    def load_meta(self, identifier: ID) -> Optional[Meta]:
        return self.database.meta(identifier=identifier)

    def save_profile(self, profile: Profile, identifier: ID=None) -> bool:
        if not self.verify_profile(profile=profile, identifier=identifier):
            raise ValueError('profile error: %s, %s' % (identifier, profile))
        return self.database.save_profile(profile=profile)

    def load_profile(self, identifier: ID) -> Optional[Profile]:
        # profile = super().load_profile(identifier=identifier)
        # if profile is not None:
        #     # profile exists in cache
        #     return profile
        return self.database.profile(identifier=identifier)

    def save_private_key(self, key: PrivateKey, identifier: ID) -> bool:
        return self.database.save_private_key(key=key, identifier=identifier)

    def load_private_key(self, identifier: ID) -> Optional[PrivateKey]:
        return self.database.private_key(identifier=identifier)

    def save_contacts(self, contacts: list, identifier: ID) -> bool:
        return self.database.save_contacts(contacts=contacts, user=identifier)

    def load_contacts(self, identifier: ID) -> Optional[list]:
        return self.database.contacts(user=identifier)

    def save_members(self, members: list, identifier: ID) -> bool:
        return self.database.save_members(members=members, group=identifier)

    def load_members(self, identifier: ID) -> Optional[list]:
        return self.database.members(group=identifier)

    def save_assistants(self, assistants: list, identifier: ID) -> bool:
        pass

    def load_assistants(self, identifier: ID) -> Optional[list]:
        assert identifier.type.is_group(), 'group ID error: %s' % identifier
        robot = self.ans.identifier(name='assistant')
        if robot is not None:
            return [robot]

    #
    #   SocialNetworkDataSource
    #
    def identifier(self, string: str) -> Optional[ID]:
        if string is None:
            return None
        if isinstance(string, ID):
            return string
        obj = self.__immortals.identifier(string=string)
        if obj is not None:
            return obj
        return super().identifier(string=string)

    #
    #   EntityDataSource
    #
    def meta(self, identifier: ID) -> Optional[Meta]:
        obj = self.__immortals.meta(identifier=identifier)
        if obj is not None:
            return obj
        return super().meta(identifier=identifier)

    def profile(self, identifier: ID) -> Optional[Profile]:
        obj = self.__immortals.profile(identifier=identifier)
        if obj is not None:
            return obj
        return super().profile(identifier=identifier)

    #
    #   UserDataSource
    #
    def private_key_for_signature(self, identifier: ID) -> Optional[PrivateKey]:
        obj = self.__immortals.private_key_for_signature(identifier=identifier)
        if obj is not None:
            return obj
        return super().private_key_for_signature(identifier=identifier)

    def private_keys_for_decryption(self, identifier: ID) -> Optional[list]:
        arr = self.__immortals.private_keys_for_decryption(identifier=identifier)
        if arr is not None:
            return arr
        return super().private_keys_for_decryption(identifier=identifier)

    def contacts(self, identifier: ID) -> Optional[list]:
        arr = self.__immortals.contacts(identifier=identifier)
        if arr is not None:
            return arr
        return super().contacts(identifier=identifier)

    #
    #    IGroupDataSource
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
