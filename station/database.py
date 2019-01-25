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
import time

import dimp

from .utils import json_dict, json_str


class Database(dimp.Barrack, dimp.KeyStore):

    def __init__(self):
        super().__init__()
        self.base_dir = '/tmp/.dim/'
        # Barrack
        self.accounts = {}
        self.groups = {}
        # KeyStore
        self.received_keys = {}
        self.sent_keys = {}

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
        receiver = msg.envelope.receiver
        directory = self.directory('public', receiver, 'messages')
        filename = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        path = directory + '/' + filename + '.msg'
        with open(path, 'a') as file:
            file.write(json_str(msg) + '\n')
        print('msg write into file: ', path)
        return True

    def load_messages(self, receiver: dimp.ID) -> list:
        directory = self.directory('public', receiver, 'messages')
        # get all files in messages directory and sort by filename
        files = sorted(os.listdir(directory))
        for filename in files:
            path = directory + '/' + filename
            if path[-4:] == '.msg':
                # read ONE .msg file for each receiver and remove the file immediately
                with open(path, 'r') as file:
                    data = file.read()
                os.remove(path)
                print('read %d byte(s) from %s' % (len(data), path))
                # ONE line ONE message, split them
                lines = str(data).splitlines()
                messages = [dimp.ReliableMessage(json_dict(line)) for line in lines]
                print('got %d message(s) for %s' % (len(messages), receiver))
                return messages

    """
        Meta file for Accounts
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/meta.js'
    """

    def save_meta(self, identifier: dimp.ID, meta: dimp.Meta) -> bool:
        if not meta.match_identifier(identifier):
            print('meta not match %s: %s, IGNORE!' % (identifier, meta))
            return False
        directory = self.directory('public', identifier)
        path = directory + '/meta.js'
        if os.path.exists(path):
            print('meta file exists: %s, update IGNORE!' % path)
        else:
            with open(path, 'w') as file:
                file.write(json_str(meta))
                print('meta write into file: ', path)
        return True

    def load_meta(self, identifier: dimp.ID) -> dimp.Meta:
        directory = self.directory('public', identifier)
        path = directory + '/meta.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                if data:
                    meta = dimp.Meta(json_dict(data))
                    if meta.match_identifier(identifier):
                        return meta
                    else:
                        raise ValueError('meta not match %s: %s' % (identifier, meta))
                else:
                    raise AssertionError('meta file empty: %s' % path)

    def process_meta_command(self, content: dimp.Content) -> dimp.Content:
        identifier = dimp.ID(content['identifier'])
        if 'meta' in content:
            # received a meta for ID
            meta = dimp.Meta(content['meta'])
            if self.save_meta(identifier=identifier, meta=meta):
                # meta saved
                command = dimp.CommandContent.new(command='receipt')
                command['message'] = 'Meta for %s received!' % identifier
                return command
            else:
                # meta not match
                return dimp.TextContent.new(text='Meta not match %s!' % identifier)
        else:
            # querying meta for ID
            meta = self.load_meta(identifier=identifier)
            if meta:
                return dimp.meta_command(identifier=identifier, meta=meta)
            else:
                return dimp.TextContent.new(text='Sorry, meta for %s not found.' % identifier)

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/private_key.js'
    """

    def save_private_key(self, identifier: dimp.ID, private_key: dimp.PrivateKey) -> bool:
        meta = self.load_meta(identifier=identifier)
        if meta is None:
            print('meta not found: %s' % identifier)
            return False
        elif not meta.key.match(private_key=private_key):
            print('private key not match %s: %s' % (identifier, private_key))
            return False
        else:
            directory = self.directory('private', identifier)
            path = directory + '/private_key.js'
            if os.path.exists(path):
                print('private key file exists: %s, update IGNORE!' % path)
            else:
                with open(path, 'w') as file:
                    file.write(json_str(private_key))
                    print('private key write into file: ', path)
            return True

    def load_private_key(self, identifier: dimp.ID) -> dimp.PrivateKey:
        directory = self.directory('private', identifier)
        path = directory + '/private_key.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                if data:
                    return dimp.PrivateKey(json_dict(data))
                else:
                    raise AssertionError('private key file empty: %s' % path)

    """
        Barrack
        ~~~~~~~
        
        Account/Group factory
    """

    def account(self, identifier: dimp.ID) -> dimp.Account:
        if identifier in self.accounts:
            return self.accounts[identifier]
        else:
            meta = self.load_meta(identifier=identifier)
            if meta:
                sk = self.load_private_key(identifier=identifier)
                if sk:
                    user = dimp.User(identifier=identifier, private_key=sk)
                else:
                    user = dimp.Account(identifier=identifier, public_key=meta.key)
                self.accounts[identifier] = user
                return user
            else:
                raise LookupError('Account meta not found: ' + identifier)

    def group(self, identifier: dimp.ID) -> dimp.Group:
        if identifier in self.groups:
            return self.groups[identifier]
        else:
            # TODO: create group
            raise LookupError('Group not found: ' + identifier)

    """
        Key Store
        ~~~~~~~~~
        
        Memory cache for reused passwords (symmetric key)
    """

    def symmetric_key(self, sender: dimp.ID=None, receiver: dimp.ID=None, parameters: dict=None) -> dimp.SymmetricKey:
        if sender:
            # got password from remote user as sender
            if sender in self.received_keys:
                return self.received_keys[sender]
            else:
                raise LookupError('Cannot find password from: ' + sender)
        else:
            # create password for remote user as receiver
            if receiver in self.sent_keys:
                return self.sent_keys[receiver]
            else:
                if parameters is None:
                    parameters = {'algorithm': 'AES'}
                key = dimp.SymmetricKey.generate(parameters)
                self.sent_keys[receiver] = key
                return key

    # def save_symmetric_key(self, key: dimp.SymmetricKey, sender: dimp.ID=None, receiver: dimp.ID=None):
    #     if sender:
    #         self.received_keys[sender] = key
    #     else:
    #         self.sent_keys[receiver] = key
