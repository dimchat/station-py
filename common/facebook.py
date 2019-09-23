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

from dimp import PrivateKey
from dimp import ID, Meta, Profile
from dimp import User, LocalUser, Group
from dimp import Command
from dimp import Barrack

from .database import Database


class Facebook(Barrack):

    def __init__(self):
        super().__init__()
        self.database: Database = None

    def save_private_key(self, private_key: PrivateKey, identifier: ID) -> bool:
        return self.database.save_private_key(private_key=private_key, identifier=identifier)

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.database.save_meta(meta=meta, identifier=identifier)

    def verify_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.database.verify_meta(meta=meta, identifier=identifier)

    def save_profile(self, profile: Profile) -> bool:
        return self.database.save_profile(profile=profile)

    def verify_profile(self, profile: Profile) -> bool:
        return self.database.verify_profile(profile=profile)

    def nickname(self, identifier: ID) -> str:
        assert identifier.type.is_user(), 'ID error: %s' % identifier
        user = self.user(identifier=identifier)
        if user is not None:
            return user.name

    def save_members(self, members: list, group: ID) -> bool:
        return self.database.save_members(members=members, group=group)

    def save_contacts_command(self, cmd: Command, sender: ID) -> bool:
        return self.database.save_contacts_command(cmd=cmd, sender=sender)

    def contacts_command(self, identifier: ID) -> Command:
        return self.database.contacts_command(identifier=identifier)

    #
    #   ISocialNetworkDataSource
    #
    def identifier(self, string: str) -> ID:
        if string is not None:
            # try from ANS record
            identifier = self.database.ans_record(name=string)
            if identifier is not None:
                return identifier
            # get from barrack
            return super().identifier(string=string)

    def user(self, identifier: ID) -> User:
        #  get from barrack cache
        user = super().user(identifier=identifier)
        if user is not None:
            return user
        # check meta and private key
        meta = self.meta(identifier=identifier)
        if meta is not None:
            key = self.private_key_for_signature(identifier=identifier)
            if key is None:
                user = User(identifier=identifier)
            else:
                user = LocalUser(identifier=identifier)
            # cache it in barrack
            self.cache_user(user=user)
            return user

    def group(self, identifier: ID) -> Group:
        # get from barrack cache
        group = super().group(identifier=identifier)
        if group is not None:
            return group
        # check meta
        meta = self.meta(identifier=identifier)
        if meta is not None:
            group = Group(identifier=identifier)
            # cache it in barrack
            self.cache_group(group=group)
            return group

    #
    #   IEntityDataSource
    #
    def meta(self, identifier: ID) -> Meta:
        #  get from barrack cache
        meta = super().meta(identifier=identifier)
        if meta is None:
            meta = self.database.meta(identifier=identifier)
            if meta is not None:
                # cache it in barrack
                self.cache_meta(meta=meta, identifier=identifier)
        return meta

    def profile(self, identifier: ID) -> Profile:
        tai = super().profile(identifier=identifier)
        if tai is None:
            tai = self.database.profile(identifier=identifier)
        return tai

    #
    #   IUserDataSource
    #
    def private_key_for_signature(self, identifier: ID) -> PrivateKey:
        return self.database.private_key(identifier=identifier)

    def private_keys_for_decryption(self, identifier: ID) -> list:
        sk = self.database.private_key(identifier=identifier)
        return [sk]

    def contacts(self, identifier: ID) -> list:
        pass

    #
    #    IGroupDataSource
    #
    def founder(self, identifier: ID) -> ID:
        # get from database
        founder = self.database.founder(group=identifier)
        if founder is not None:
            return founder
        return super().founder(identifier=identifier)

    def owner(self, identifier: ID) -> ID:
        # get from database
        owner = self.database.owner(group=identifier)
        if owner is not None:
            return owner
        return super().owner(identifier=identifier)

    def members(self, identifier: ID) -> list:
        # get from database
        members = self.database.members(group=identifier)
        if members is not None:
            return members
        return super().members(identifier=identifier)
