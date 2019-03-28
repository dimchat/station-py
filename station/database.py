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
import json

import dimp

from .utils import base64_decode
from .apns import IAPNsDelegate


class Database(dimp.Barrack, dimp.KeyStore, IAPNsDelegate):

    def __init__(self):
        super().__init__()
        self.base_dir = '/tmp/.dim/'

    def directory(self, control: str, identifier: dimp.ID, sub_dir: str='') -> str:
        path = self.base_dir + control + '/' + identifier.address
        if sub_dir:
            path = path + '/' + sub_dir
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        
        file path: '.dim/public/{ADDRESS}/messages/*.msg'
    """

    def store_message(self, msg: dimp.ReliableMessage) -> bool:
        receiver = dimp.ID(msg.envelope.receiver)
        directory = self.directory('public', receiver, 'messages')
        filename = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        path = directory + '/' + filename + '.msg'
        with open(path, 'a') as file:
            file.write(json.dumps(msg) + '\n')
        print('msg write into file: ', path)
        return True

    def load_message_batch(self, receiver: dimp.ID) -> dict:
        directory = self.directory('public', receiver, 'messages')
        # get all files in messages directory and sort by filename
        files = sorted(os.listdir(directory))
        for filename in files:
            if filename[-4:] == '.msg':
                path = directory + '/' + filename
                # read ONE .msg file for each receiver and remove the file immediately
                with open(path, 'r') as file:
                    data = file.read()
                os.remove(path)
                print('read %d byte(s) from %s' % (len(data), path))
                # ONE line ONE message, split them
                lines = str(data).splitlines()
                messages = [dimp.ReliableMessage(json.loads(line)) for line in lines]
                print('got %d message(s) for %s' % (len(messages), receiver))
                return {'ID': receiver, 'filename': filename, 'path': path, 'messages': messages}

    def remove_message_batch(self, batch: dict, removed_count: int) -> bool:
        if removed_count <= 0:
            print('message count to removed error:', removed_count)
            return False
        # 0. get message file path
        path = batch.get('path')
        if path is None:
            receiver = batch.get('ID')
            filename = batch.get('filename')
            if receiver and filename:
                directory = self.directory('pubic', receiver, 'messages')
                path = directory + '/' + filename
        if not os.path.exists(path):
            print('message file not exists: %s' % path)
            return False
        # 1. remove all message(s)
        print('remove message file: %s' % path)
        os.remove(path)
        # 2. store the rest messages back
        messages = batch.get('messages')
        if messages is None:
            return False
        total_count = len(messages)
        if removed_count < total_count:
            # remove message(s) partially
            messages = messages[:removed_count]
            for msg in messages:
                with open(path, 'a') as file:
                    file.write(json.dumps(msg) + '\n')
            print('the rest messages(%d) write back into file: ', path)
        return True

    """
        Meta file for Accounts
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/meta.js'
    """

    def cache_meta(self, meta: dimp.Meta, identifier: dimp.ID) -> bool:
        if not super().cache_meta(meta=meta, identifier=identifier):
            print('meta not match %s: %s, IGNORE!' % (identifier, meta))
            return False
        # save meta as new file
        directory = self.directory('public', identifier)
        path = directory + '/meta.js'
        if os.path.exists(path):
            print('meta file exists: %s, update IGNORE!' % path)
        else:
            with open(path, 'w') as file:
                file.write(json.dumps(meta))
            print('meta write into file: ', path)
        # meta cached
        return True

    def meta(self, identifier: dimp.ID) -> dimp.Meta:
        meta = super().meta(identifier=identifier)
        if meta is not None:
            return meta
        # load from local storage
        directory = self.directory('public', identifier)
        path = directory + '/meta.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                # no need to check meta again
                meta = dimp.Meta(json.loads(data))
                # update memory cache
                self.cache_meta(meta=meta, identifier=identifier)
                return meta

    """
        Profile for Accounts
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/profile.js'
    """

    def save_profile_signature(self, identifier: dimp.ID, profile: str, signature: str) -> bool:
        meta = self.meta(identifier=identifier)
        if meta:
            pk = meta.key
            data = profile.encode('utf-8')
            sig = base64_decode(signature)
            if not pk.verify(data, sig):
                print('signature not match %s: %s, %s' % (identifier, profile, signature))
                return False
        else:
            print('meta not found: %s, IGNORE!' % identifier)
            return False
        # save/update profile
        content = {
            'ID': identifier,
            'profile': profile,
            'signature': signature,
        }
        directory = self.directory('public', identifier)
        path = directory + '/profile.js'
        with open(path, 'w') as file:
            file.write(json.dumps(content))
        print('profile write into file: ', path)
        # update memory cache
        profile = json.loads(profile)
        return self.cache_profile(profile=profile, identifier=identifier)

    def profile_signature(self, identifier: dimp.ID) -> dict:
        # load from local storage
        directory = self.directory('public', identifier)
        path = directory + '/profile.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                content = json.loads(data)
                # no need to check signature again
                return content

    def profile(self, identifier: dimp.ID) -> dict:
        content = super().profile(identifier=identifier)
        if content is not None:
            return content
        # load from local storage
        content = self.profile_signature(identifier=identifier)
        if content and 'profile' in content:
            profile = content.get('profile')
            content = json.loads(profile)
        self.cache_profile(profile=content, identifier=identifier)
        return content

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/private_key.js'
    """

    def cache_private_key(self, private_key: dimp.PrivateKey, identifier: dimp.ID) -> bool:
        if super().cache_private_key(private_key=private_key, identifier=identifier):
            # save private key as new file
            directory = self.directory('private', identifier)
            path = directory + '/private_key.js'
            if os.path.exists(path):
                print('private key file exists: %s, update IGNORE!' % path)
            else:
                with open(path, 'w') as file:
                    file.write(json.dumps(private_key))
                print('private key write into file: ', path)
            return True
        else:
            print('cannot update private key: %s -> %s' % (private_key, identifier))
            return False

    def private_key(self, identifier: dimp.ID) -> dimp.PrivateKey:
        sk = super().private_key(identifier=identifier)
        if sk is not None:
            return sk
        # load from local storage
        directory = self.directory('private', identifier)
        path = directory + '/private_key.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                sk = dimp.PrivateKey(json.loads(data))
                # update memory cache
                self.cache_private_key(private_key=sk, identifier=identifier)
                return sk

    """
        Key Store
        ~~~~~~~~~
        
        Memory cache for reused passwords (symmetric key)
    """

    def cipher_key(self, sender: dimp.ID, receiver: dimp.ID) -> dimp.SymmetricKey:
        key = super().cipher_key(sender=sender, receiver=receiver)
        if key is not None:
            return key
        # create a new key & save it into the Key Store
        key = dimp.SymmetricKey.generate({'algorithm': 'AES'})
        self.cache_cipher_key(key=key, sender=sender, receiver=receiver)
        return key

    def flush(self):
        if self.dirty is False or self.user is None:
            return
        # write key table to persistent storage
        directory = self.directory('public', self.user.identifier)
        path = directory + '/keystore.js'
        with open(path, 'w') as file:
            file.write(self.key_table)
        print('keystore write into file: ', path)
        self.dirty = False

    def key_exists(self, sender_address: str, receiver_address: str) -> bool:
        key_map = self.key_table.get(sender_address)
        if key_map is None:
            return False
        return receiver_address in key_map

    def reload(self) -> bool:
        if self.user is None:
            return False
        # load key table from persistent storage
        directory = self.directory('public', self.user.identifier)
        path = directory + '/keystore.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                table_ = json.loads(data)
                # key_table[sender.address] -> key_map
                for from_, map_ in table_:
                    key_map = self.key_table.get(from_)
                    if key_map is None:
                        key_map = {}
                        self.key_table[from_] = key_map
                    # key_map[receiver.address] -> key
                    for to_, key_ in map_:
                        # update memory cache
                        key_map[to_] = dimp.SymmetricKey(key_)

    """
        Search Engine
        ~~~~~~~~~~~~~
        
        Search accounts by the 'Search Number'
    """

    def search(self, keywords: list) -> dict:
        results = {}
        max_count = 20
        for identifier in self.accounts:
            identifier = dimp.ID(identifier)
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
                max_count = max_count-1
                if max_count <= 0:
                    break
        return results

    """
        APNs Delegate
        ~~~~~~~~~~~~~
    """
    def device_tokens(self, identifier: str) -> list:
        directory = self.directory('private', dimp.ID(identifier))
        path = directory + '/device.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                device = json.loads(data)
                return device.get('tokens')

    def cache_device_token(self, identifier: str, token: str) -> bool:
        if token is None:
            return False
        directory = self.directory('private', dimp.ID(identifier))
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
            tokens.append(token)
        device['tokens'] = tokens
        # 3. save device info
        with open(path, 'w') as file:
            file.write(json.dumps(device))
        print('device token flush into file: %s, %s' % (path, device))
        return True
