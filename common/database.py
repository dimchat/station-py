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
    Database
    ~~~~~~~~

    for cached messages, profile manage(Barrack), reused symmetric keys(KeyStore)
"""

import os
import time
import random
import json

from dimp import SymmetricKey, PrivateKey
from dimp import ID, Meta, Profile
from dimp import Account, User, Group
from dimp import IUserDataSource, IGroupDataSource, ICipherKeyDataSource

from dimp import ReliableMessage
from dimp import Transceiver

from .log import Log
from .facebook import facebook, barrack
from .keystore import keystore


class Database(IUserDataSource, IGroupDataSource, ICipherKeyDataSource):

    def __init__(self):
        super().__init__()
        # memory cache
        self.__metas = {}
        self.__profiles = {}
        self.__private_keys = {}

        self.base_dir = '/tmp/.dim/'

    def __directory(self, control: str, identifier: ID, sub_dir: str = '') -> str:
        path = self.base_dir + control + '/' + identifier.address
        if sub_dir:
            path = path + '/' + sub_dir
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def cache_private_key(self, private_key: PrivateKey, identifier: ID):
        self.__private_keys[identifier.address] = private_key

    #
    #   IEntityDataSource
    #
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        self.__metas[identifier.address] = meta
        # save meta as new file
        directory = self.__directory('public', identifier)
        path = directory + '/meta.js'
        if os.path.exists(path):
            Log.info('[DB] meta file exists: %s, update IGNORE!' % path)
        else:
            with open(path, 'w') as file:
                file.write(json.dumps(meta))
            Log.info('[DB] meta write into file: %s' % path)
        # meta cached
        return True

    def meta(self, identifier: ID) -> Meta:
        return self.load_meta(identifier=identifier)

    def profile(self, identifier: ID) -> Profile:
        # TODO: load profile from local storage
        return self.load_profile(identifier=identifier)

    #
    #   IUserDataSource
    #
    def private_key_for_signature(self, identifier: ID) -> PrivateKey:
        # TODO: load private key from keychain
        return self.load_private_key(identifier=identifier)

    def private_keys_for_decryption(self, identifier: ID) -> list:
        # TODO: load private key from keychain
        key = self.load_private_key(identifier=identifier)
        return [key]

    def contacts(self, identifier: ID) -> list:
        # TODO: load contacts from local storage
        pass

    #
    #   IGroupDataSource
    #
    def founder(self, identifier: ID) -> ID:
        # TODO: load group info from local storage
        pass

    def owner(self, identifier: ID) -> ID:
        # TODO: load group info from local storage
        pass

    def members(self, identifier: ID) -> list:
        # TODO: load group info from local storage
        pass

    #
    #   IBarrackDelegate
    #
    def account(self, identifier: ID) -> Account:
        return facebook.account(identifier=identifier)

    def user(self, identifier: ID) -> User:
        return facebook.user(identifier=identifier)

    def group(self, identifier: ID) -> Group:
        return facebook.group(identifier=identifier)

    #
    #   ICipherKeyDataSource
    #
    def cipher_key(self, sender: ID, receiver: ID) -> SymmetricKey:
        return keystore.cipher_key(sender=sender, receiver=receiver)

    def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID) -> bool:
        return keystore.cache_cipher_key(key=key, sender=sender, receiver=receiver)

    def reuse_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID) -> SymmetricKey:
        # TODO: update/create cipher key
        pass

    #
    #   IAPNsDelegate
    #
    def device_tokens(self, identifier: str) -> list:
        return self.load_device_tokens(identifier=identifier)

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/private_key.js'
    """

    def save_private_key(self, private_key: PrivateKey, identifier: ID):
        self.__private_keys[identifier.address] = private_key
        # save private key as new file
        directory = self.__directory('private', identifier)
        path = directory + '/private_key.js'
        if os.path.exists(path):
            Log.info('[DB] private key file exists: %s, update IGNORE!' % path)
        else:
            with open(path, 'w') as file:
                file.write(json.dumps(private_key))
            Log.info('[DB] private key write into file: %s' % path)

    def load_private_key(self, identifier: ID) -> PrivateKey:
        sk = self.__private_keys.get(identifier.address)
        if sk is None:
            # load from local storage
            directory = self.__directory('private', identifier)
            path = directory + '/private_key.js'
            if os.path.exists(path):
                with open(path, 'r') as file:
                    data = file.read()
                sk = PrivateKey(json.loads(data))
                # update memory cache
                self.__private_keys[identifier.address] = sk
        return sk

    """
        Meta file for entities
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/meta.js'
    """

    def load_meta(self, identifier: ID) -> Meta:
        meta = self.__metas.get(identifier.address)
        if meta is None:
            # load from local storage
            directory = self.__directory('public', identifier)
            path = directory + '/meta.js'
            if os.path.exists(path):
                with open(path, 'r') as file:
                    data = file.read()
                meta = Meta(json.loads(data))
                # update memory cache
                self.__metas[identifier.address] = meta
        return meta

    """
        Profile for Accounts
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/profile.js'
    """

    def cache_profile(self, profile: Profile) -> bool:
        identifier = profile.identifier
        meta = self.meta(identifier=identifier)
        if meta is None:
            Log.info('[DB] meta not found: %s, IGNORE!' % identifier)
            return False
        if not profile.verify(meta.key):
            Log.info('[DB] profile signature not match: %s' % profile)
            return False
        # update memory cache
        self.__profiles[identifier.address] = profile
        return True

    def save_profile(self, profile: Profile) -> bool:
        if not self.cache_profile(profile=profile):
            return False
        # save/update profile
        identifier = profile.identifier
        directory = self.__directory('public', identifier)
        path = directory + '/profile.js'
        with open(path, 'w') as file:
            file.write(json.dumps(profile))
        Log.info('[DB] profile write into file: %s' % path)
        return True

    def load_profile(self, identifier: ID) -> Profile:
        profile = self.__profiles.get(identifier.address)
        if profile is not None:
            return profile
        # load from local storage
        directory = self.__directory('public', identifier)
        path = directory + '/profile.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
            content = json.loads(data)
            # compatible with v1.0
            data = content.get('data')
            if data is None:
                data = content.get('profile')
                if data is not None:
                    content['data'] = data
                    content.pop('profile')
            # verify & cache
            profile = Profile(content)
            if self.cache_profile(profile):
                return content

    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/device.js'
    """

    def load_device_tokens(self, identifier: str) -> list:
        directory = self.__directory('protected', ID(identifier))
        path = directory + '/device.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
            device = json.loads(data)
            # TODO: only get the last two devices
            return device.get('tokens')

    def save_device_token(self, identifier: str, token: str) -> bool:
        if token is None:
            return False
        directory = self.__directory('protected', ID(identifier))
        path = directory + '/device.js'
        # 1. load device info
        device = None
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
            device = json.loads(data)
        if device is None:
            device = {}
        # 2. get tokens list for updating
        tokens = device.get('tokens')
        if tokens is None:
            tokens = [token]
        elif token not in tokens:
            # TODO: only save the last two devices
            tokens.append(token)
        device['tokens'] = tokens
        # 3. save device info
        with open(path, 'w') as file:
            file.write(json.dumps(device))
        Log.info('[DB] device token flush into file: %s, %s' % (path, device))
        return True

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/messages/*.msg'
    """

    def store_message(self, msg: ReliableMessage) -> bool:
        receiver = ID(msg.envelope.receiver)
        directory = self.__directory('public', receiver, 'messages')
        filename = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        path = directory + '/' + filename + '.msg'
        with open(path, 'a') as file:
            file.write(json.dumps(msg) + '\n')
        Log.info('[DB] msg write into file: %s' % path)
        return True

    def load_message_batch(self, receiver: ID) -> dict:
        directory = self.__directory('public', receiver, 'messages')
        # get all files in messages directory and sort by filename
        files = sorted(os.listdir(directory))
        for filename in files:
            if filename[-4:] == '.msg':
                path = directory + '/' + filename
                # read ONE .msg file for each receiver and remove the file immediately
                with open(path, 'r') as file:
                    lines = file.readlines()
                Log.info('[DB] read %d line(s) from %s' % (len(lines), path))
                # messages = [ReliableMessage(json.loads(line)) for line in lines]
                messages = []
                for line in lines:
                    msg = line.strip()
                    if len(msg) == 0:
                        Log.info('[DB] skip empty line')
                        continue
                    try:
                        msg = json.loads(msg)
                        msg = ReliableMessage(msg)
                        messages.append(msg)
                    except Exception as error:
                        Log.info('[DB] message package error %s, %s' % (error, line))
                Log.info('[DB] got %d message(s) for %s' % (len(messages), receiver))
                if len(messages) == 0:
                    Log.info('[DB] remove empty message file %s' % path)
                    os.remove(path)
                return {'ID': receiver, 'filename': filename, 'path': path, 'messages': messages}

    def remove_message_batch(self, batch: dict, removed_count: int) -> bool:
        if removed_count <= 0:
            Log.info('[DB] message count to removed error: %d' % removed_count)
            return False
        # 0. get message file path
        path = batch.get('path')
        if path is None:
            receiver = batch.get('ID')
            filename = batch.get('filename')
            if receiver and filename:
                directory = self.__directory('pubic', receiver, 'messages')
                path = directory + '/' + filename
        if not os.path.exists(path):
            Log.info('[DB] message file not exists: %s' % path)
            return False
        # 1. remove all message(s)
        Log.info('[DB] remove message file: %s' % path)
        os.remove(path)
        # 2. store the rest messages back
        messages = batch.get('messages')
        if messages is None:
            return False
        total_count = len(messages)
        if removed_count < total_count:
            # remove message(s) partially
            messages = messages[removed_count:]
            for msg in messages:
                with open(path, 'a') as file:
                    file.write(json.dumps(msg) + '\n')
            Log.info('[DB] the rest messages(%d) write back into file: %s' % path)
        return True

    """
        Search Engine
        ~~~~~~~~~~~~~

        Search accounts by the 'Search Number'
    """

    def search(self, keywords: list) -> dict:
        results = {}
        max_count = 20
        array = list(barrack.accounts.keys())
        array = random.sample(array, len(array))
        for identifier in array:
            identifier = ID(identifier)
            network = identifier.address.network
            if not network.is_person() and not network.is_group():
                # ignore
                continue
            match = True
            for kw in keywords:
                if identifier.find(kw) < 0 and ('%010d' % identifier.number).find(kw) < 0:
                    # not match
                    match = False
                    break
            if not match:
                continue
            # got it
            meta = self.meta(identifier)
            if meta:
                results[identifier] = meta
                # force to stop
                max_count = max_count - 1
                if max_count <= 0:
                    break
        return results


database = Database()

barrack.entityDataSource = database
barrack.userDataSource = database
barrack.groupDataSource = database

transceiver = Transceiver()
transceiver.delegate = facebook
transceiver.barrackDelegate = database
transceiver.entityDataSource = database
transceiver.cipherKeyDataSource = database
