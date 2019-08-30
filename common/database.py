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

from dimp import PrivateKey
from dimp import ID, Meta, Profile
from dimp import ReliableMessage

from database import MetaTable, PrivateKeyTable, ProfileTable, DeviceTable
from .log import Log


def scan_ids(database):
    # ids = []
    # # scan all metas
    # directory = database.base_dir + 'public'
    # # get all files in messages directory and sort by filename
    # files = os.listdir(directory)
    # for filename in files:
    #     path = directory + '/' + filename + '/meta.js'
    #     if not os.path.exists(path):
    #         # Log.info('meta file not exists: %s' % path)
    #         continue
    #     identifier = ID(filename)
    #     if identifier is None:
    #         # Log.info('error: %s' % filename)
    #         continue
    #     meta = database.meta(identifier=identifier)
    #     if meta is None:
    #         Log.info('meta error: %s' % identifier)
    #     # Log.info('loaded meta for %s from %s: %s' % (identifier, path, meta))
    #     ids.append(meta.generate_identifier(network=identifier.type))
    # Log.info('loaded %d id(s) from %s' % (len(ids), directory))
    # return ids
    table = MetaTable()
    return table.scan_ids()


class Database:

    def __init__(self):
        super().__init__()
        # memory cache
        # self.__metas = {}
        # self.__profiles = {}
        # self.__private_keys = {}

        self.base_dir = '/tmp/.dim/'

    def __directory(self, control: str, identifier: ID, sub_dir: str = '') -> str:
        path = self.base_dir + control + '/' + identifier.address
        if sub_dir:
            path = path + '/' + sub_dir
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/private_key.js'
    """
    # def cache_private_key(self, private_key: PrivateKey, identifier: ID) -> bool:
    #     assert identifier.valid, 'failed to cache private key for ID: %s' % identifier
    #     if private_key is None:
    #         return False
    #     # update memory cache
    #     self.__private_keys[identifier] = private_key
    #     return True

    def save_private_key(self, private_key: PrivateKey, identifier: ID) -> bool:
        # if not self.cache_private_key(private_key=private_key, identifier=identifier):
        #     return False
        # # save private key as new file
        # directory = self.__directory('private', identifier)
        # path = directory + '/private_key.js'
        # if os.path.exists(path):
        #     Log.info('[DB] private key file exists: %s, update IGNORE!' % path)
        # else:
        #     with open(path, 'w') as file:
        #         file.write(json.dumps(private_key))
        #     Log.info('[DB] private key write into file: %s' % path)
        # return True
        table = PrivateKeyTable()
        return table.save_private_key(private_key=private_key, identifier=identifier)

    def private_key(self, identifier: ID) -> PrivateKey:
        # sk = self.__private_keys.get(identifier)
        # if sk is not None:
        #     return sk
        # # load from local storage
        # directory = self.__directory('private', identifier)
        # path = directory + '/private_key.js'
        # if os.path.exists(path):
        #     with open(path, 'r') as file:
        #         data = file.read()
        #     sk = PrivateKey(json.loads(data))
        #     # update memory cache
        #     self.cache_private_key(private_key=sk, identifier=identifier)
        #     return sk
        table = PrivateKeyTable()
        return table.private_key(identifier=identifier)

    """
        Meta file for entities
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/meta.js'
    """
    # def cache_meta(self, meta: Meta, identifier: ID) -> bool:
    #     assert identifier.valid, 'failed to cache meta for ID: %s' % identifier
    #     if meta is None:
    #         return False
    #     # update memory cache
    #     self.__metas[identifier] = meta
    #     return True

    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        # if not self.cache_meta(meta=meta, identifier=identifier):
        #     return False
        # # save meta as new file
        # directory = self.__directory('public', identifier)
        # path = directory + '/meta.js'
        # if os.path.exists(path):
        #     Log.info('[DB] meta file exists: %s, update IGNORE!' % path)
        # else:
        #     with open(path, 'w') as file:
        #         file.write(json.dumps(meta))
        #     Log.info('[DB] meta write into file: %s' % path)
        # return True
        table = MetaTable()
        return table.save_meta(meta=meta, identifier=identifier)

    def meta(self, identifier: ID) -> Meta:
        # meta = self.__metas.get(identifier)
        # if meta is not None:
        #     return meta
        # load from local storage
        # directory = self.__directory('public', identifier)
        # path = directory + '/meta.js'
        # if os.path.exists(path):
        #     with open(path, 'r') as file:
        #         data = file.read()
        #     meta = Meta(json.loads(data))
        #     # update memory cache
        #     self.cache_meta(meta=meta, identifier=identifier)
        #     return meta
        table = MetaTable()
        return table.meta(identifier=identifier)

    """
        Profile for Accounts
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/profile.js'
    """
    # def cache_profile(self, profile: Profile) -> bool:
    #     identifier = profile.identifier
    #     assert identifier.valid, 'failed to cache profile for ID: %s' % identifier
    #     meta = self.meta(identifier=identifier)
    #     if meta is None:
    #         Log.info('[DB] meta not found: %s, IGNORE!' % identifier)
    #         return False
    #     if not profile.verify(meta.key):
    #         Log.info('[DB] profile signature not match: %s' % profile)
    #         return False
    #     # update memory cache
    #     self.__profiles[identifier.address] = profile
    #     return True

    def save_profile(self, profile: Profile) -> bool:
        # if not self.cache_profile(profile=profile):
        #     return False
        # # save/update profile
        # identifier = profile.identifier
        # directory = self.__directory('public', identifier)
        # path = directory + '/profile.js'
        # with open(path, 'w') as file:
        #     file.write(json.dumps(profile))
        # Log.info('[DB] profile write into file: %s' % path)
        # return True
        table = ProfileTable()
        return table.save_profile(profile=profile)

    def profile(self, identifier: ID) -> Profile:
        # profile = self.__profiles.get(identifier)
        # if profile is not None:
        #     return profile
        # # load from local storage
        # directory = self.__directory('public', identifier)
        # path = directory + '/profile.js'
        # if os.path.exists(path):
        #     with open(path, 'r') as file:
        #         data = file.read()
        #     content = json.loads(data)
        #     # compatible with v1.0
        #     data = content.get('data')
        #     if data is None:
        #         data = content.get('profile')
        #         if data is not None:
        #             content['data'] = data
        #             content.pop('profile')
        #     profile = Profile(content)
        #     # update memory cache
        #     self.cache_profile(profile)
        #     return profile
        table = ProfileTable()
        return table.profile(identifier=identifier)

    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/device.js'
    """

    #
    #   IAPNsDelegate
    #
    def device_tokens(self, identifier: str) -> list:
        # directory = self.__directory('protected', ID(identifier))
        # path = directory + '/device.js'
        # if os.path.exists(path):
        #     with open(path, 'r') as file:
        #         data = file.read()
        #     device = json.loads(data)
        #     # TODO: only get the last two devices
        #     return device.get('tokens')
        table = DeviceTable()
        return table.device_tokens(identifier=ID(identifier))

    def save_device_token(self, identifier: str, token: str) -> bool:
        # if token is None:
        #     return False
        # directory = self.__directory('protected', ID(identifier))
        # path = directory + '/device.js'
        # # 1. load device info
        # device = None
        # if os.path.exists(path):
        #     with open(path, 'r') as file:
        #         data = file.read()
        #     device = json.loads(data)
        # if device is None:
        #     device = {}
        # # 2. get tokens list for updating
        # tokens = device.get('tokens')
        # if tokens is None:
        #     tokens = [token]
        # elif token not in tokens:
        #     # TODO: only save the last two devices
        #     tokens.append(token)
        # device['tokens'] = tokens
        # # 3. save device info
        # with open(path, 'w') as file:
        #     file.write(json.dumps(device))
        # Log.info('[DB] device token flush into file: %s, %s' % (path, device))
        # return True
        table = DeviceTable()
        return table.save_device_token(token=token, identifier=ID(identifier))

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
        # results = {}
        # max_count = 20
        # array = scan_ids(self)
        # array = random.sample(array, len(array))
        # for identifier in array:
        #     identifier = ID(identifier)
        #     network = identifier.type
        #     if not network.is_person():
        #         # ignore
        #         continue
        #     match = True
        #     for kw in keywords:
        #         if identifier.find(kw) < 0 and ('%010d' % identifier.number).find(kw) < 0:
        #             # not match
        #             match = False
        #             break
        #     if not match:
        #         continue
        #     # got it
        #     meta = self.meta(identifier)
        #     if meta:
        #         results[identifier] = meta
        #         # force to stop
        #         max_count = max_count - 1
        #         if max_count <= 0:
        #             break
        # return results
        table = MetaTable()
        return table.search(keywords=keywords)
