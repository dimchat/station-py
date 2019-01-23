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
                    with open(path, 'r') as f:
                        data = f.read()
                    print('read %d byte(s) from %s for %s' % (len(data), filename, identifier))
                    if data is not None:
                        msg = dimp.ReliableMessage(json_dict(data))
                    os.remove(path)
                    return msg

    def account(self, identifier: dimp.ID) -> dimp.Account:
        if identifier in self.accounts:
            return self.accounts[identifier]
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
