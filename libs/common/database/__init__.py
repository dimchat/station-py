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

from typing import Optional, List

from dimp import PrivateKey, SignKey, DecryptKey
from dimp import ID, Meta, Document
from dimp import Command
from dimp import ReliableMessage
from dimsdk import LoginCommand

from ...utils import Singleton

from .storage import Storage
from .private_table import PrivateKeyTable
from .meta_table import MetaTable
from .document_table import DocumentTable, DeviceTable
from .user_table import UserTable
from .group_table import GroupTable
from .message_table import MessageTable, MessageBundle
from .ans_table import AddressNameTable

from .login_table import LoginTable


__all__ = [
    'Storage',
    # 'MetaTable', 'DocumentTable', 'PrivateKeyTable',
    # 'DeviceTable',
    # 'MessageTable',
    'MessageBundle',
    # 'AddressNameTable',
    'Database',
]


@Singleton
class Database:

    def __init__(self):
        super().__init__()
        # data tables
        self.__private_table = PrivateKeyTable()
        self.__meta_table = MetaTable()
        self.__document_table = DocumentTable()
        self.__device_table = DeviceTable()
        self.__user_table = UserTable()
        self.__group_table = GroupTable()
        self.__message_table = MessageTable()
        # ANS
        self.__ans_table = AddressNameTable()
        # login info
        self.__login_table = LoginTable()

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/secret.js'
    """
    def save_private_key(self, key: PrivateKey, identifier: ID, key_type: str = 'M'):
        return self.__private_table.save_private_key(key=key, identifier=identifier, key_type=key_type)

    def private_keys_for_decryption(self, identifier: ID) -> List[DecryptKey]:
        return self.__private_table.private_keys_for_decryption(identifier=identifier)

    def private_key_for_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__private_table.private_key_for_signature(identifier=identifier)

    def private_key_for_visa_signature(self, identifier: ID) -> Optional[SignKey]:
        return self.__private_table.private_key_for_visa_signature(identifier=identifier)

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
    def save_document(self, document: Document) -> bool:
        if not document.valid:
            identifier = document.identifier
            if identifier is None:
                return False
            meta = self.meta(identifier=identifier)
            if meta is None:
                return False
            if not document.verify(public_key=meta.key):
                return False
        return self.__document_table.save_document(document=document)

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Document:
        return self.__document_table.document(identifier=identifier, doc_type=doc_type)

    """
        User contacts
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts.txt'
    """
    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        return self.__user_table.save_contacts(contacts=contacts, user=user)

    def contacts(self, user: ID) -> List[ID]:
        return self.__user_table.contacts(user=user)

    """
        Stored Contacts for User
        ~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts_stored.js'
    """
    def save_contacts_command(self, cmd: Command, sender: ID) -> bool:
        return self.__user_table.save_contacts_command(cmd=cmd, sender=sender)

    def contacts_command(self, identifier: ID) -> Optional[Command]:
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

    def is_blocked(self, receiver: ID, sender: ID, group: ID = None) -> bool:
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

    def is_muted(self, receiver: ID, sender: ID, group: ID = None) -> bool:
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
    #   APNs Delegate
    #
    def device_tokens(self, identifier: ID) -> List[str]:
        return self.__device_table.device_tokens(identifier=identifier)

    """
        Group members
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/members.txt'
    """
    def save_members(self, members: List[ID], group: ID) -> bool:
        return self.__group_table.save_members(members=members, group=group)

    def members(self, group: ID) -> List[ID]:
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
    def message_bundle(self, identifier: ID) -> MessageBundle:
        return self.__message_table.message_bundle(identifier=identifier)

    def store_message(self, msg: ReliableMessage) -> bool:
        return self.__message_table.store_message(msg=msg)

    def erase_message(self, msg: ReliableMessage) -> bool:
        return self.__message_table.erase_message(msg=msg)

    """
        Scan all documents from data directory
    """
    def scan_documents(self) -> List[Document]:
        return self.__document_table.scan_documents()

    """
        Address Name Service
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/ans.txt'
    """
    def ans_save_record(self, name: str, identifier: ID) -> bool:
        return self.__ans_table.save_record(name=name, identifier=identifier)

    def ans_record(self, name: str) -> ID:
        return self.__ans_table.record(name=name)

    def ans_names(self, identifier: ID) -> List[str]:
        return self.__ans_table.names(identifier=identifier)

    """
        Login Info
        ~~~~~~~~~~
        
        file path: '.dim/public/{ADDRESS}/login.js'
    """
    def save_login(self, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        return self.__login_table.save_login(cmd=cmd, msg=msg)

    def login_command(self, identifier: ID) -> Optional[LoginCommand]:
        return self.__login_table.login_command(identifier=identifier)

    def login_message(self, identifier: ID) -> Optional[ReliableMessage]:
        return self.__login_table.login_message(identifier=identifier)

    def login_info(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        return self.__login_table.login_info(identifier=identifier)
