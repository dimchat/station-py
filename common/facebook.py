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
import json

from mkm.crypto.utils import base64_encode

from dimp import ID, NetworkID, Meta, Profile, Account, User, Group
from dimp import Barrack, ICompletionHandler, ITransceiverDelegate

from .log import Log


class Facebook(ITransceiverDelegate):

    def __init__(self):
        super().__init__()
        # default delegate for entities
        self.entityDataSource = None

    def nickname(self, identifier: ID) -> str:
        account = self.account(identifier=identifier);
        if account is not None:
            return account.name

    #
    #   IBarrackDelegate
    #
    def identifier(self, string) -> ID:
        # TODO: create ID
        identifier = ID(identifier=string)
        return identifier

    def account(self, identifier: ID) -> Account:
        # TODO: create account
        entity = Account(identifier=identifier)
        entity.delegate = self.entityDataSource
        return entity

    def user(self, identifier: ID) -> User:
        # TODO: create user
        entity = User(identifier=identifier)
        entity.delegate = self.entityDataSource
        return entity

    def group(self, identifier: ID) -> Group:
        # TODO: create group
        entity = Group(identifier=identifier)
        entity.delegate = self.entityDataSource
        return entity

    #
    #   ITransceiverDelegate
    #
    def send_package(self, data: bytes, handler: ICompletionHandler) -> bool:
        pass


barrack = Barrack()
facebook = Facebook()

facebook.entityDataSource = barrack
barrack.delegate = facebook


def scan_ids(database):
    ids = []
    # scan all metas
    directory = database.base_dir + 'public'
    # get all files in messages directory and sort by filename
    files = os.listdir(directory)
    for filename in files:
        path = directory + '/' + filename + '/meta.js'
        if not os.path.exists(path):
            # Log.info('meta file not exists: %s' % path)
            continue
        identifier = ID(filename)
        if identifier is None:
            # Log.info('error: %s' % filename)
            continue
        meta = database.load_meta(identifier=identifier)
        if meta is None:
            Log.info('meta error: %s' % identifier)
        # Log.info('loaded meta for %s from %s: %s' % (identifier, path, meta))
        ids.append(meta.generate_identifier(network=identifier.type))
    Log.info('loaded %d id(s) from %s' % (len(ids), directory))
    return ids


def load_accounts(database):
    Log.info('======== loading accounts')

    #
    # load immortals
    #

    from .immortals import moki_id, moki_name, moki_pk, moki_sk, moki_meta, moki_profile, moki
    from .immortals import hulk_id, hulk_name, hulk_pk, hulk_sk, hulk_meta, hulk_profile, hulk
    from .providers import s001_id, s001_name, s001_pk, s001_sk, s001_meta, s001_profile, s001

    Log.info('loading immortal user: %s' % moki_id)
    database.save_meta(identifier=moki_id, meta=moki_meta)
    database.save_private_key(identifier=moki_id, private_key=moki_sk)
    database.cache_profile(profile=moki_profile)

    Log.info('loading immortal user: %s' % hulk_id)
    database.save_meta(identifier=hulk_id, meta=hulk_meta)
    database.save_private_key(identifier=hulk_id, private_key=hulk_sk)
    database.cache_profile(profile=hulk_profile)

    Log.info('loading station: %s' % s001_id)
    database.save_meta(identifier=s001_id, meta=s001_meta)
    database.save_private_key(identifier=s001_id, private_key=s001_sk)
    database.cache_profile(profile=s001_profile)

    barrack.cache_account(account=moki)
    barrack.cache_account(account=hulk)
    barrack.cache_account(account=s001)

    # store station name
    profile = '{\"name\":\"%s\"}' % s001_name
    signature = base64_encode(s001_sk.sign(profile.encode('utf-8')))
    profile = {
        'ID': s001_id,
        'data': profile,
        'signature': signature,
    }
    profile = Profile(profile)
    database.save_profile(profile=profile)

    #
    # scan accounts
    #

    scan_ids(database)

    Log.info('======== loaded')
