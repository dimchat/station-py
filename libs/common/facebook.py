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

from typing import Optional

from dimp import PrivateKey, SignKey
from dimp import ID, Meta, Profile, User
from dimsdk import Facebook
from dimsdk.immortals import Immortals

from .database import Database


class CommonFacebook(Facebook):

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
        assert identifier.is_user, 'user ID error: %s' % identifier
        profile = self.profile(identifier=identifier)
        if profile is not None:
            name = profile.name
            if name is not None and len(name) > 0:
                return name
        return identifier.name

    def group_name(self, identifier: ID) -> str:
        assert identifier.is_group, 'group ID error: %s' % identifier
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
        self.__local_users = array

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.database.save_meta(meta=meta, identifier=identifier)

    def save_profile(self, profile: Profile, identifier: ID=None) -> bool:
        return self.database.save_profile(profile=profile)

    def save_private_key(self, key: PrivateKey, identifier: ID) -> bool:
        return self.database.save_private_key(key=key, identifier=identifier)

    def save_contacts(self, contacts: list, identifier: ID) -> bool:
        return self.database.save_contacts(contacts=contacts, user=identifier)

    def save_members(self, members: list, identifier: ID) -> bool:
        return self.database.save_members(members=members, group=identifier)

    def save_assistants(self, assistants: list, identifier: ID) -> bool:
        pass

    #
    #   SocialNetworkDataSource
    #

    # def identifier(self, string: str) -> Optional[ID]:
    #     if string is None:
    #         return None
    #     if isinstance(string, ID):
    #         return string
    #     return super().identifier(string=string)

    #
    #   EntityDataSource
    #

    def meta(self, identifier: ID) -> Optional[Meta]:
        info = self.database.meta(identifier=identifier)
        if info is not None:
            return info
        return self.__immortals.meta(identifier=identifier)

    def profile(self, identifier: ID) -> Optional[Profile]:
        info = self.database.profile(identifier=identifier)
        if info is not None:
            return info
        return self.__immortals.profile(identifier=identifier)

    #
    #   UserDataSource
    #

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        key = self.database.private_key(identifier=identifier)
        if key is not None:
            return key
        return self.__immortals.private_key_for_signature(identifier=identifier)

    def private_keys_for_decryption(self, identifier: ID) -> Optional[list]:
        key = self.database.private_key(identifier=identifier)
        if key is not None:
            return [key]
        return self.__immortals.private_keys_for_decryption(identifier=identifier)

    def contacts(self, identifier: ID) -> Optional[list]:
        array = self.database.contacts(user=identifier)
        if array is None:
            # create empty list for cache
            array = []
            self.database.cache_contacts(contacts=array, identifier=identifier)
        elif len(array) > 0 and not isinstance(array[0], ID):
            # convert IDs
            tmp = []
            for item in array:
                tmp.append(self.identifier(string=item))
            array = tmp
            self.database.cache_contacts(contacts=array, identifier=identifier)
        return array

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

    def members(self, identifier: ID) -> Optional[list]:
        array = self.database.members(group=identifier)
        if array is None:
            # create empty list for cache
            array = []
            self.database.cache_members(members=array, identifier=identifier)
        elif len(array) > 0 and not isinstance(array[0], ID):
            # convert IDs
            tmp = []
            for item in array:
                tmp.append(self.identifier(string=item))
            array = tmp
            self.database.cache_members(members=array, identifier=identifier)
        return array

    def assistants(self, identifier: ID) -> Optional[list]:
        assert identifier.is_group, 'group ID error: %s' % identifier
        robot = self.ans.identifier(name='assistant')
        if robot is not None:
            return [robot]
