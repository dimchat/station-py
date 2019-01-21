# -*- coding: utf-8 -*-

import dimp

from station.config import station


class Barrack(dimp.Barrack):

    def __init__(self):
        super().__init__()
        self.accounts = {}
        self.groups = {}

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


class KeyStore(dimp.KeyStore):

    def __init__(self):
        super().__init__()
        self.received_keys = {}
        self.sent_keys = {}

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


barrack = Barrack()
store = KeyStore()

transceiver = dimp.Transceiver(account=station,
                               private_key=station.privateKey,
                               barrack=barrack,
                               store=store)
