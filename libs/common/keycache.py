# -*- coding: utf-8 -*-
#
#   DIMP : Decentralized Instant Messaging Protocol
#
#                                Written in 2019 by Moky <albert.moky@gmail.com>
#
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
    Symmetric Keys Cache
    ~~~~~~~~~~~~~~~~~~~~

    Manage keys for conversations
"""

from abc import abstractmethod
from typing import Optional

from dimsdk.plugins import PlainKey
from dimsdk import SymmetricKey, ID
from dimsdk import CipherKeyDelegate

plain_key = PlainKey({'algorithm': PlainKey.PLAIN})


class KeyCache(CipherKeyDelegate):

    def __init__(self):
        super().__init__()
        # memory cache
        self.__key_map = {}
        self.__dirty = False

    def reload(self) -> bool:
        """ Trigger for loading cipher key table """
        dictionary = self.load_keys()
        if dictionary is None:
            return False
        return self.update_keys(dictionary)

    def flush(self):
        """ Trigger for saving cipher key table """
        if self.__dirty and self.save_keys(self.__key_map):
            # keys saved
            self.__dirty = False

    @abstractmethod
    def save_keys(self, key_map: dict) -> bool:
        """
        Callback for saving cipher key table into local storage

        :param key_map: all cipher keys(with direction) from memory cache
        :return:        True on success
        """
        pass

    @abstractmethod
    def load_keys(self) -> Optional[dict]:
        """
        Load cipher key table from local storage

        :return: keys map
        """
        pass

    def update_keys(self, key_map: dict) -> bool:
        """
        Update cipher key table into memory cache

        :param key_map: cipher keys(with direction) from local storage
        :return:        False on nothing changed
        """
        changed = False
        for _from in key_map:
            sender = ID(_from)
            table = key_map.get(_from)
            assert isinstance(table, dict), 'sender table error: %s, %s' % (_from, table)
            for _to in table:
                receiver = ID(_to)
                pw = table.get(_to)
                key = SymmetricKey(pw)
                # TODO: check whether exists an old key
                changed = True
                # cache key with direction
                self.__cache_cipher_key(key, sender, receiver)
        return changed

    def __cipher_key(self, sender: ID, receiver: ID) -> Optional[SymmetricKey]:
        assert sender.valid and receiver.valid, 'error: (%s -> %s)' % (sender, receiver)
        table = self.__key_map.get(sender)
        if table is not None:
            return table.get(receiver)

    def __cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        assert sender.valid and receiver.valid and key is not None, 'error: (%s -> %s) %s' % (sender, receiver, key)
        table = self.__key_map.get(sender)
        if table is None:
            table = {}
            self.__key_map[sender] = table
        else:
            old = table.get(receiver)
            if old is not None:
                # check whether same key exists
                equals = True
                assert isinstance(key, dict), 'key info error: %s' % key
                for k in key:
                    v1 = key.get(k)
                    v2 = old.get(k)
                    if v1 == v2:
                        continue
                    equals = False
                    break
                if equals:
                    # no need to update
                    return
        table[receiver] = key

    #
    #   CipherKeyDelegate
    #

    # TODO: override to check whether key expired for sending message
    def cipher_key(self, sender: ID, receiver: ID) -> Optional[SymmetricKey]:
        if receiver.is_broadcast:
            return plain_key
        # get key from cache
        return self.__cipher_key(sender, receiver)

    def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        if receiver.is_broadcast:
            return
        self.__cache_cipher_key(key, sender, receiver)
        self.__dirty = True
