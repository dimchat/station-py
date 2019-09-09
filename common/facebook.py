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

from mkm.crypto.utils import base64_encode

from dimp import PrivateKey
from dimp import ID, NetworkID, Meta, Profile
from dimp import User, LocalUser, Group
from dimp import Barrack

from database import Database

from .log import Log


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
        user = self.user(identifier=identifier)
        if user is not None:
            return user.name

    def save_members(self, members: list, group: ID) -> bool:
        return self.database.save_members(members=members, group=group)

    #
    #   ISocialNetworkDataSource
    #
    def user(self, identifier: ID) -> User:
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
            self.cache_user(user=user)
            return user

    def group(self, identifier: ID) -> Group:
        group = super().group(identifier=identifier)
        if group is not None:
            return group
        # check meta
        meta = self.meta(identifier=identifier)
        if meta is not None:
            # create group
            group = Group(identifier=identifier)
            self.cache_group(group=group)
            return group

    #
    #   IEntityDataSource
    #
    def meta(self, identifier: ID) -> Meta:
        meta = super().meta(identifier=identifier)
        if meta is None:
            meta = self.database.meta(identifier=identifier)
            if meta is not None:
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
        meta = self.meta(identifier=identifier)
        members = self.members(identifier=identifier)
        if meta is not None and members is not None:
            for identifier in members:
                m = self.meta(identifier=identifier)
                if m is not None and meta.match_public_key(m.key):
                    return identifier

    def owner(self, identifier: ID) -> ID:
        if identifier.type.value == NetworkID.Polylogue:
            return self.founder(identifier=identifier)

    def members(self, identifier: ID) -> list:
        return self.database.members(group=identifier)


def load_accounts(facebook):
    Log.info('======== loading accounts')

    #
    # load immortals
    #

    from .immortals import moki_id, moki_name, moki_pk, moki_sk, moki_meta, moki_profile, moki
    from .immortals import hulk_id, hulk_name, hulk_pk, hulk_sk, hulk_meta, hulk_profile, hulk
    from .providers import s001_id, s001_name, s001_pk, s001_sk, s001_meta, s001_profile, s001

    Log.info('loading immortal user: %s' % moki_id)
    facebook.save_meta(identifier=moki_id, meta=moki_meta)
    facebook.save_private_key(identifier=moki_id, private_key=moki_sk)
    facebook.save_profile(profile=moki_profile)

    Log.info('loading immortal user: %s' % hulk_id)
    facebook.save_meta(identifier=hulk_id, meta=hulk_meta)
    facebook.save_private_key(identifier=hulk_id, private_key=hulk_sk)
    facebook.save_profile(profile=hulk_profile)

    Log.info('loading station: %s' % s001_id)
    facebook.save_meta(identifier=s001_id, meta=s001_meta)
    facebook.save_private_key(identifier=s001_id, private_key=s001_sk)
    facebook.save_profile(profile=s001_profile)

    # store station name
    profile = '{\"name\":\"%s\"}' % s001_name
    signature = base64_encode(s001_sk.sign(profile.encode('utf-8')))
    profile = {
        'ID': s001_id,
        'data': profile,
        'signature': signature,
    }
    profile = Profile(profile)
    facebook.save_profile(profile=profile)

    #
    # scan accounts
    #

    facebook.database.scan_ids()

    Log.info('======== loaded')
