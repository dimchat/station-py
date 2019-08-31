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

from dimp import PrivateKey
from dimp import NetworkID, ID, Meta, Profile
from dimp import ReliableMessage

from .storage import Storage
from .meta_table import MetaTable
from .profile_table import ProfileTable, DeviceTable
from .private_table import PrivateKeyTable
from .message_table import MessageTable


__all__ = [
    'MetaTable', 'ProfileTable', 'PrivateKeyTable',
    'DeviceTable',
    'MessageTable',

    'Database',
]


class Database:

    def __init__(self):
        super().__init__()
        # data tables
        self.__private_table = PrivateKeyTable()
        self.__meta_table = MetaTable()
        self.__profile_table = ProfileTable()
        self.__device_table = DeviceTable()
        self.__message_table = MessageTable()

    @property
    def base_dir(self) -> str:
        return Storage.root

    @base_dir.setter
    def base_dir(self, root: str):
        Storage.root = root

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/private_key.js'
    """
    def save_private_key(self, private_key: PrivateKey, identifier: ID) -> bool:
        return self.__private_table.save_private_key(private_key=private_key, identifier=identifier)

    def private_key(self, identifier: ID) -> PrivateKey:
        return self.__private_table.private_key(identifier=identifier)

    """
        Meta file for entities
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/meta.js'
    """
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        return self.__meta_table.save_meta(meta=meta, identifier=identifier)

    def meta(self, identifier: ID) -> Meta:
        return self.__meta_table.meta(identifier=identifier)

    """
        Profile for Accounts
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/profile.js'
    """
    def save_profile(self, profile: Profile) -> bool:
        if not profile.valid:
            # try to verify the profile
            identifier = profile.identifier
            assert identifier.valid, 'profile ID not valid: %s' % profile
            if identifier.type.is_user() or identifier.type.value == NetworkID.Polylogue:
                # if this is a user profile,
                #     verify it with the user's meta.key
                # else if this is a polylogue profile,
                #     verify it with the founder's meta.key
                meta = self.meta(identifier=identifier)
                if meta is not None:
                    profile.verify(public_key=meta.key)
            else:
                raise NotImplementedError('unsupported profile ID: %s' % profile)
        return self.__profile_table.save_profile(profile=profile)

    def profile(self, identifier: ID) -> Profile:
        return self.__profile_table.profile(identifier=identifier)

    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/device.js'
    """
    def save_device_token(self, identifier: str, token: str) -> bool:
        return self.__device_table.save_device_token(token=token, identifier=ID(identifier))

    #
    #   IAPNsDelegate
    #
    def device_tokens(self, identifier: str) -> list:
        return self.__device_table.device_tokens(identifier=ID(identifier))

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/messages/*.msg'
    """
    def store_message(self, msg: ReliableMessage) -> bool:
        return self.__message_table.store_message(msg=msg)

    def load_message_batch(self, receiver: ID) -> dict:
        return self.__message_table.load_message_batch(receiver=receiver)

    def remove_message_batch(self, batch: dict, removed_count: int) -> bool:
        return self.__message_table.remove_message_batch(batch=batch, removed_count=removed_count)

    """
        Search Engine
        ~~~~~~~~~~~~~

        Search accounts by the 'Search Number'
    """
    def search(self, keywords: list) -> dict:
        return self.__meta_table.search(keywords=keywords)

    def scan_ids(self):
        return self.__meta_table.scan_ids()
