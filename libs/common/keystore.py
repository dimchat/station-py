# -*- coding: utf-8 -*-
#
#   DIM-SDK : Decentralized Instant Messaging Software Development Kit
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
    Key Store
    ~~~~~~~~~

    Memory cache for reused passwords (symmetric key)
"""

import os
from typing import Optional

from dimp import User
from dimsdk.dos import JSONFile

from .keycache import KeyCache


class KeyStore(KeyCache):

    def __init__(self):
        super().__init__()
        self.__user: User = None
        self.__base_dir: str = '/tmp/.dim/'

    @property
    def user(self) -> Optional[User]:
        return self.__user

    @user.setter
    def user(self, value: User):
        if self.__user is not None:
            # save key map for old user
            self.flush()
            if self.__user == value:
                # user not changed
                return
        if value is None:
            self.__user = None
            return
        # change current user
        self.__user = value
        keys = self.load_keys()
        if keys is None:
            # failed to load cached keys for new user
            return
        # update key map
        self.update_keys(key_map=keys)

    @property
    def directory(self) -> str:
        return self.__base_dir

    @directory.setter
    def directory(self, value: str):
        self.__base_dir = value

    # '/tmp/.dim/protected/{ADDRESS}/keystore.js'
    def __path(self) -> Optional[str]:
        if self.__user is None:
            return None
        return os.path.join(self.__base_dir, 'protected', self.__user.identifier, 'keystore.js')

    def save_keys(self, key_map: dict) -> bool:
        # write key table to persistent storage
        path = self.__path()
        if path is None:
            return False
        return JSONFile(path).write(key_map)

    def load_keys(self) -> Optional[dict]:
        # load key table from persistent storage
        path = self.__path()
        if path is None:
            return None
        return JSONFile(path).read()
