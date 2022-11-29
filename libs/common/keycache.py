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

    Memory cache for reused conversation passwords (symmetric key)
"""

from typing import Optional

from dimsdk import SymmetricKey, ID
from dimsdk import CipherKeyDelegate
from dimsdk import PlainKey

from ..utils import Singleton
from ..database import Database


plain_key = PlainKey({'algorithm': PlainKey.PLAIN})


@Singleton
class KeyCache(CipherKeyDelegate):

    def __init__(self):
        super().__init__()
        self.__db = Database()

    #
    #   CipherKeyDelegate
    #

    # TODO: override to check whether key expired for sending message
    def cipher_key(self, sender: ID, receiver: ID, generate: bool = False) -> Optional[SymmetricKey]:
        if receiver.is_broadcast:
            return plain_key
        # get key from cache
        key = self.__db.cipher_key(sender=sender, receiver=receiver)
        if key is None and generate:
            # generate and cache it
            key = SymmetricKey.generate(algorithm=SymmetricKey.AES)
            assert key is not None, 'failed to generate key'
            self.__db.cache_cipher_key(key=key, sender=sender, receiver=receiver)
        return key

    def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID) -> bool:
        if receiver.is_broadcast:
            # no need to store cipher key for broadcast message
            return False
        return self.__db.cache_cipher_key(key=key, sender=sender, receiver=receiver)
