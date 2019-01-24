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

from station.utils import json_dict, json_str


class Database(dimp.Barrack, dimp.KeyStore):

    def __init__(self):
        super().__init__()
        self.base_dir = '/tmp/dim/'
        # Barrack
        self.accounts = {}
        self.groups = {}
        # KeyStore
        self.received_keys = {}
        self.sent_keys = {}

    def store_message(self, msg: dimp.ReliableMessage) -> bool:
        receiver = msg.envelope.receiver
        directory = self.base_dir + 'accounts/' + receiver.address + '/messages'
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        path = directory + '/' + filename + '.msg'
        with open(path, 'w') as file:
            file.write(json_str(msg))
            print('msg write into file: ', path)
        return True

    def load_message(self, identifier: dimp.ID) -> dimp.ReliableMessage:
        directory = self.base_dir + 'accounts/' + identifier.address + '/messages'
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                path = os.path.join(directory, filename)
                if path[-4:] == '.msg':
                    with open(path, 'r') as file:
                        data = file.read()
                    print('read %d byte(s) from %s for %s' % (len(data), filename, identifier))
                    if data is not None:
                        msg = dimp.ReliableMessage(json_dict(data))
                    else:
                        msg = None
                    os.remove(path)
                    return msg

    def save_meta(self, identifier: dimp.ID, meta: dimp.Meta) -> bool:
        if not meta.match_identifier(identifier):
            print('meta not match %s: %s, IGNORE!' %(identifier, meta))
            return False
        directory = self.base_dir + 'accounts/' + identifier.address
        path = directory + '/meta.js'
        if os.path.exists(path):
            print('meta file already exists, no need to update %s, IGNORE!' % path)
        else:
            if not os.path.exists(directory):
                os.makedirs(directory)
            with open(path, 'w') as file:
                file.write(json_str(meta))
                print('meta write into file: ', path)
        return True

    def load_meta(self, identifier: dimp.ID) -> dimp.Meta:
        path = self.base_dir + 'accounts/' + identifier.address + '/meta.js'
        if os.path.exists(path):
            with open(path, 'r') as file:
                data = file.read()
                if data:
                    meta = dimp.Meta(json_dict(data))
                    if meta.match_identifier(identifier=identifier):
                        return meta
                    else:
                        raise ValueError('meta not match %s: %s' % (identifier, meta))
                else:
                    raise AssertionError('meta file empty: %s' % path)
        else:
            raise LookupError('meta not found: %s' % identifier)

    def account(self, identifier: dimp.ID) -> dimp.Account:
        if identifier in self.accounts:
            return self.accounts[identifier]
        else:
            meta = self.load_meta(identifier=identifier)
            if meta:
                a = dimp.Account(identifier=identifier, public_key=meta.key)
                self.accounts[identifier] = a
                return a
            else:
                raise LookupError('Account not found: ' + identifier)

    def group(self, identifier: dimp.ID) -> dimp.Group:
        if identifier in self.groups:
            return self.groups[identifier]
        else:
            raise LookupError('Group not found: ' + identifier)

    def symmetric_key(self, sender: dimp.ID=None, receiver: dimp.ID=None) -> dimp.SymmetricKey:
        if sender:
            if sender in self.received_keys:
                return self.received_keys[sender]
            else:
                raise LookupError('Cannot find password from: ' + sender)
        else:
            if receiver in self.sent_keys:
                return self.sent_keys[receiver]
            else:
                password = dimp.SymmetricKey.generate({'algorithm': 'AES'})
                self.sent_keys[receiver] = password
                return password

    def save_symmetric_key(self, password: dimp.SymmetricKey, sender: dimp.ID=None, receiver: dimp.ID=None):
        if sender:
            self.received_keys[sender] = password
        else:
            self.sent_keys[receiver] = password
