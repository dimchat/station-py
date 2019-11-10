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
    Database module
    ~~~~~~~~~~~~~~~

"""

from dimp import PrivateKey
from dimp import ID, Meta, Profile
from dimp import Command
from dimp import ReliableMessage

from .storage import Storage
from .private_table import PrivateKeyTable
from .meta_table import MetaTable
from .profile_table import ProfileTable, DeviceTable
from .user_table import UserTable
from .group_table import GroupTable
from .message_table import MessageTable
from .ans_table import AddressNameTable


__all__ = [
    'Storage',
    # 'MetaTable', 'ProfileTable', 'PrivateKeyTable',
    # 'DeviceTable',
    # 'MessageTable',
    # 'AddressNameTable',
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
        self.__user_table = UserTable()
        self.__group_table = GroupTable()
        self.__message_table = MessageTable()
        # ANS
        self.__ans_table = AddressNameTable()

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
        return self.__profile_table.save_profile(profile=profile)

    def profile(self, identifier: ID) -> Profile:
        return self.__profile_table.profile(identifier=identifier)

    """
        User contacts
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts.txt'
    """
    def save_contacts(self, contacts: list, user: ID) -> bool:
        return self.__user_table.save_contacts(contacts=contacts, user=user)

    def contacts(self, user: ID) -> list:
        return self.__user_table.contacts(user=user)

    """
        Contacts of User
        ~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts_stored.js'
    """
    def save_contacts_command(self, cmd: Command, sender: ID) -> bool:
        return self.__user_table.save_contacts_command(cmd=cmd, sender=sender)

    def contacts_command(self, identifier: ID) -> Command:
        return self.__user_table.contacts_command(identifier=identifier)

    """
        Block-list of User
        ~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/block_stored.js'
    """
    def save_block_command(self, cmd: Command, sender: ID) -> bool:
        return self.__user_table.save_block_command(cmd=cmd, sender=sender)

    def block_command(self, identifier: ID) -> Command:
        return self.__user_table.block_command(identifier=identifier)

    def is_blocked(self, receiver: ID, sender: ID, group: ID=None) -> bool:
        cmd = self.block_command(identifier=receiver)
        if cmd is None:
            return False
        array = cmd.get('list')
        if array is None:
            return False
        if group is None:
            # check for personal message
            return sender in array
        else:
            # check for group message
            return group in array

    """
        Mute-list of User
        ~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/mute_stored.js'
    """
    def save_mute_command(self, cmd: Command, sender: ID) -> bool:
        return self.__user_table.save_mute_command(cmd=cmd, sender=sender)

    def mute_command(self, identifier: ID) -> Command:
        return self.__user_table.mute_command(identifier=identifier)

    def is_muted(self, receiver: ID, sender: ID, group: ID=None) -> bool:
        cmd = self.mute_command(identifier=receiver)
        if cmd is None:
            return False
        array = cmd.get('list')
        if array is None:
            return False
        if group is None:
            # check for personal message
            return sender in array
        else:
            # check for group message
            return group in array

    """
        Device Tokens for APNS
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/device.js'
    """
    def save_device_token(self, token: str, identifier: ID) -> bool:
        return self.__device_table.save_device_token(token=token, identifier=identifier)

    #
    #   IAPNsDelegate
    #
    def device_tokens(self, identifier: str) -> list:
        identifier = Storage.identifier(string=identifier)
        return self.__device_table.device_tokens(identifier=identifier)

    """
        Group members
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/members.txt'
    """
    def save_members(self, members: list, group: ID) -> bool:
        return self.__group_table.save_members(members=members, group=group)

    def members(self, group: ID) -> list:
        return self.__group_table.members(group=group)

    def founder(self, group: ID) -> ID:
        return self.__group_table.founder(group=group)

    def owner(self, group: ID) -> ID:
        return self.__group_table.owner(group=group)

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

    """
        Address Name Service
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/ans.txt'
    """
    def ans_save_record(self, name: str, identifier: ID) -> bool:
        return self.__ans_table.save_record(name=name, identifier=identifier)

    def ans_record(self, name: str) -> ID:
        return self.__ans_table.record(name=name)

    def ans_names(self, identifier: ID) -> list:
        return self.__ans_table.names(identifier=identifier)
