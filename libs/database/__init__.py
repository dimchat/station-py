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

from typing import Optional, List, Set, Dict

from dimp import PrivateKey, SignKey, DecryptKey
from dimp import ID, Meta, Document
from dimp import Command
from dimp import ReliableMessage
from dimsdk import LoginCommand

from ..utils import Singleton

from .dos import Storage

from .cache import CachePool, CacheHolder, CacheCleaner
from .cache import FrequencyChecker
from .table_network import NetworkTable
from .table_ans import AddressNameTable
from .table_private import PrivateKeyTable
from .table_meta import MetaTable
from .table_document import DocumentTable
from .table_device import DeviceTable
from .table_user import UserTable
from .table_login import LoginTable
from .table_group import GroupTable
from .table_session import SessionTable
from .table_message import MessageTable


__all__ = [
    'Storage',

    'CachePool', 'CacheHolder', 'CacheCleaner',
    'FrequencyChecker',

    'NetworkTable',
    'AddressNameTable',

    'MetaTable',
    'DocumentTable', 'DeviceTable',
    'UserTable', 'PrivateKeyTable', 'LoginTable',
    'GroupTable',
    'SessionTable',
    'MessageTable',

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
        # Session
        self.__session_table = SessionTable()
        # Network
        self.__network_table = NetworkTable()
        # ANS
        self.__ans_table = AddressNameTable()
        # login info
        self.__login_table = LoginTable()

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/secret.js'
        file path: '.dim/private/{ADDRESS}/secret_keys.js'
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
        redis key: 'mkm.meta.{ID}'
    """
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        if Meta.matches(meta=meta, identifier=identifier):
            # no need to update existed meta
            if self.meta(identifier=identifier) is None:
                return self.__meta_table.save_meta(meta=meta, identifier=identifier)
            else:
                return True

    def meta(self, identifier: ID) -> Optional[Meta]:
        return self.__meta_table.meta(identifier=identifier)

    """
        Document for Accounts
        ~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/profile.js'
        redis key: 'mkm.document.{ID}'
        redis key: 'mkm.docs.keys'
    """
    def save_document(self, document: Document) -> bool:
        # check with meta first
        meta = self.meta(identifier=document.identifier)
        assert meta is not None, 'meta not exists: %s' % document
        # check document valid before saving it
        if document.valid or document.verify(public_key=meta.key):
            return self.__document_table.save_document(document=document)

    def document(self, identifier: ID, doc_type: Optional[str] = '*') -> Optional[Document]:
        return self.__document_table.document(identifier=identifier, doc_type=doc_type)

    def scan_documents(self) -> List[Document]:
        return self.__document_table.scan_documents()

    """
        User contacts
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts.txt'
        redis key: 'mkm.user.{ID}.contacts'
    """
    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        return self.__user_table.save_contacts(contacts=contacts, user=user)

    def contacts(self, user: ID) -> List[ID]:
        return self.__user_table.contacts(user=user)

    """
        Stored Contacts for User
        ~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts_stored.js'
        redis key: 'mkm.user.{ID}.cmd.contacts'
    """
    def save_contacts_command(self, cmd: Command, sender: ID) -> bool:
        return self.__user_table.save_contacts_command(cmd=cmd, sender=sender)

    def contacts_command(self, identifier: ID) -> Optional[Command]:
        return self.__user_table.contacts_command(identifier=identifier)

    """
        Block-list of User
        ~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/block_stored.js'
        redis key: 'mkm.user.{ID}.cmd.block'
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
        redis key: 'mkm.user.{ID}.cmd.mute'
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
        redis key: 'dim.user.{ID}.device'
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
        redis key: 'mkm.group.{ID}.members'
    """
    def save_group_members(self, members: List[ID], group: ID) -> bool:
        return self.__group_table.save_members(members=members, group=group)

    def group_members(self, group: ID) -> List[ID]:
        return self.__group_table.members(group=group)

    def group_founder(self, group: ID) -> ID:
        return self.__group_table.founder(group=group)

    def group_owner(self, group: ID) -> ID:
        return self.__group_table.owner(group=group)

    def update_group_keys(self, keys: Dict[str, str], sender: ID, group: ID) -> bool:
        return self.__group_table.update_keys(keys=keys, sender=sender, group=group)

    def group_keys(self, sender: ID, group: ID) -> Optional[Dict[str, str]]:
        return self.__group_table.get_keys(sender=sender, group=group)

    def group_key(self, sender: ID, member: ID, group: ID) -> Optional[str]:
        return self.__group_table.get_key(sender=sender, member=member, group=group)

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'dkd.msg.{ID}.{sig}'
        redis key: 'dkd.msg.{ID}.messages'
    """
    def save_message(self, msg: ReliableMessage) -> bool:
        return self.__message_table.save_message(msg=msg)

    def remove_message(self, msg: ReliableMessage) -> bool:
        return self.__message_table.remove_message(msg=msg)

    def messages(self, receiver: ID) -> List[ReliableMessage]:
        return self.__message_table.messages(receiver=receiver)

    """
        Session info
        ~~~~~~~~~~~~
        
        redis key: 'mkm.session.{ID}.addresses'
        redis key: 'mkm.session.{address}.info'
    """
    def active_sessions(self, identifier: ID) -> Set[dict]:
        return self.__session_table.active_sessions(identifier=identifier)

    def fetch_session(self, address: tuple) -> dict:
        return self.__session_table.fetch_session(address=address)

    def update_session(self, address: tuple, identifier: ID) -> bool:
        return self.__session_table.update_session(address=address, identifier=identifier)

    def renew_session(self, address: tuple, identifier: Optional[ID]) -> bool:
        return self.__session_table.renew_session(address=address, identifier=identifier)

    """
        Address Name Service
        ~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/ans.txt'
        redis key: 'dim.ans'
    """
    def ans_save_record(self, name: str, identifier: ID) -> bool:
        return self.__ans_table.save_record(name=name, identifier=identifier)

    def ans_record(self, name: str) -> ID:
        return self.__ans_table.record(name=name)

    def ans_names(self, identifier: ID) -> Set[str]:
        return self.__ans_table.names(identifier=identifier)

    """
        Login Info
        ~~~~~~~~~~
        
        redis key: 'mkm.user.{ID}.login'
    """
    def save_login(self, cmd: LoginCommand, msg: ReliableMessage) -> bool:
        return self.__login_table.save_login(cmd=cmd, msg=msg)

    def login_command(self, identifier: ID) -> Optional[LoginCommand]:
        return self.__login_table.login_command(identifier=identifier)

    def login_message(self, identifier: ID) -> Optional[ReliableMessage]:
        return self.__login_table.login_message(identifier=identifier)

    def login_info(self, identifier: ID) -> (Optional[LoginCommand], Optional[ReliableMessage]):
        return self.__login_table.login_info(identifier=identifier)

    """
        Online / Offline
        ~~~~~~~~~~~~~~~~
        
        redis key: 'mkm.user.{ID}.online'
        redis key: 'mkm.user.{ID}.offline'
    """
    def save_online(self, cmd: Command, msg: ReliableMessage) -> bool:
        return self.__login_table.save_online(cmd=cmd, msg=msg)

    def save_offline(self, cmd: Command, msg: ReliableMessage) -> bool:
        return self.__login_table.save_offline(cmd=cmd, msg=msg)

    def online_command(self, identifier: ID) -> Optional[Command]:
        return self.__login_table.online_command(identifier=identifier)

    def offline_command(self, identifier: ID) -> Optional[Command]:
        return self.__login_table.offline_command(identifier=identifier)

    """
        Network Info
        ~~~~~~~~~~~~
        
        redis key: 'dim.network.query.meta'
        redis key: 'dim.network.query.document'
    """

    def add_meta_query(self, identifier: ID):
        return self.__network_table.add_meta_query(identifier=identifier)

    def pop_meta_query(self) -> Optional[ID]:
        return self.__network_table.pop_meta_query()

    def add_document_query(self, identifier: ID):
        return self.__network_table.add_document_query(identifier=identifier)

    def pop_document_query(self) -> Optional[ID]:
        return self.__network_table.pop_document_query()

    def add_online_user(self, station: ID, user: ID, login_time: int = None):
        self.__network_table.add_online_user(station=station, user=user, login_time=login_time)

    def remove_offline_users(self, station: ID, users: List[ID]):
        self.__network_table.remove_offline_users(station=station, users=users)

    def get_online_users(self, station: ID, start: int = 0, limit: int = -1) -> List[ID]:
        return self.__network_table.get_online_users(station=station, start=start, limit=limit)
