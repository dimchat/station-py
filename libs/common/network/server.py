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
    Station Server
    ~~~~~~~~~~~~~~

    Local station
"""

from typing import Optional

from dimp import ID, PrivateKey, UserDataSource
from dimsdk import Station


class Server(Station):
    """
        Local Station
        ~~~~~~~~~~~~~
    """

    def __init__(self, identifier: ID, host: str, port: int=9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.running = False

    def __sign_key(self) -> PrivateKey:
        assert isinstance(self.delegate, UserDataSource), 'user delegate error: %s' % self.delegate
        return self.delegate.private_key_for_signature(identifier=self.identifier)

    def __decrypt_keys(self) -> list:
        assert isinstance(self.delegate, UserDataSource), 'user delegate error: %s' % self.delegate
        return self.delegate.private_keys_for_decryption(identifier=self.identifier)

    def sign(self, data: bytes) -> bytes:
        """
        Sign data with user's private key

        :param data: message data
        :return: signature
        """
        key = self.__sign_key()
        return key.sign(data=data)

    def decrypt(self, data: bytes) -> Optional[bytes]:
        """
        Decrypt data with user's private key(s)

        :param data: ciphertext
        :return: plaintext
        """
        keys = self.__decrypt_keys()
        # try decrypting it with each private key
        for key in keys:
            try:
                plaintext = key.decrypt(data=data)
                if plaintext is not None:
                    # OK!
                    return plaintext
            except ValueError:
                # this key not match, try next one
                continue
