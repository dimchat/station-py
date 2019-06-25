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

from dkd.utils import base64_encode

from dimp import ID, NetworkID, Meta, Profile, Account, User, Group
from dimp import Barrack, IBarrackDelegate

from .log import Log


class Facebook(IBarrackDelegate):

    #
    #   IBarrackDelegate
    #
    def account(self, identifier: ID) -> Account:
        # TODO: create account
        entity = Account(identifier=identifier)
        entity.delegate = barrack
        return entity

    def user(self, identifier: ID) -> User:
        # TODO: create user
        entity = User(identifier=identifier)
        entity.delegate = barrack
        return entity

    def group(self, identifier: ID) -> Group:
        # TODO: create group
        entity = Group(identifier=identifier)
        entity.delegate = barrack
        return entity


barrack = Barrack()
facebook = Facebook()


def load_accounts(database):
    Log.info('======== loading accounts')

    from .immortals import moki_id, moki_name, moki_pk, moki_sk, moki_meta, moki_profile, moki
    from .immortals import hulk_id, hulk_name, hulk_pk, hulk_sk, hulk_meta, hulk_profile, hulk
    from .providers import s001_id, s001_name, s001_pk, s001_sk, s001_meta, s001_profile, s001

    Log.info('loading immortal user: %s' % moki_id)
    database.save_meta(identifier=moki_id, meta=moki_meta)
    database.save_private_key(identifier=moki_id, private_key=moki_sk)

    Log.info('loading immortal user: %s' % hulk_id)
    database.save_meta(identifier=hulk_id, meta=hulk_meta)
    database.save_private_key(identifier=hulk_id, private_key=hulk_sk)

    Log.info('loading station: %s' % s001_id)
    database.save_meta(identifier=s001_id, meta=s001_meta)
    database.save_private_key(identifier=s001_id, private_key=s001_sk)
    barrack.cache_account(s001)
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

    # scan all metas
    directory = database.base_dir + 'public'
    # get all files in messages directory and sort by filename
    files = sorted(os.listdir(directory))
    for filename in files:
        path = directory + '/' + filename + '/meta.js'
        if os.path.exists(path):
            Log.info('loading %s' % path)
            with open(path, 'r') as file:
                data = file.read()
                # no need to check meta again
            meta = Meta(json.loads(data))
            identifier = meta.generate_identifier(network=NetworkID.Main)
            if barrack.account(identifier=identifier):
                # already exists
                continue
            if path.endswith(identifier.address + '/meta.js'):
                # address matched
                sk = database.load_private_key(identifier=identifier)
                if sk:
                    user = User(identifier=identifier)
                    # database.accounts[identifier] = user
                    barrack.cache_account(user)
                else:
                    account = Account(identifier=identifier)
                    # database.accounts[identifier] = account
                    barrack.cache_account(account)

    Log.info('======== loaded')
