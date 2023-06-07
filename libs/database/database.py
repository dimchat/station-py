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

from typing import Optional, List, Set, Tuple

from dimples import SymmetricKey, PrivateKey, SignKey, DecryptKey
from dimples import ID, Meta, Document
from dimples import ReliableMessage

from dimples import Command, LoginCommand
from dimples import AccountDBI, MessageDBI, SessionDBI
from dimples.common.dbi import ProviderInfo, StationInfo
from dimples.database.t_private import PrivateKeyTable
from dimples.database.t_cipherkey import CipherKeyTable

from ..common import BlockCommand, MuteCommand

# from .t_ans import AddressNameTable
from .t_meta import MetaTable
from .t_document import DocumentTable
from .t_device import DeviceTable
from .t_user import UserTable
from .t_login import LoginTable
from .t_active import ActiveTable
from .t_group import GroupTable
from .t_message import MessageTable
from .t_station import StationTable


class Database(AccountDBI, MessageDBI, SessionDBI):

    def __init__(self, root: str = None, public: str = None, private: str = None):
        super().__init__()
        # Entity
        self.__private_table = PrivateKeyTable(root=root, public=public, private=private)
        self.__meta_table = MetaTable(root=root, public=public, private=private)
        self.__document_table = DocumentTable(root=root, public=public, private=private)
        self.__device_table = DeviceTable(root=root, public=public, private=private)
        self.__user_table = UserTable(root=root, public=public, private=private)
        self.__group_table = GroupTable(root=root, public=public, private=private)
        self.__msg_key_table = CipherKeyTable(root=root, public=public, private=private)
        # Message
        self.__message_table = MessageTable(root=root, public=public, private=private)
        # # ANS
        # self.__ans_table = AddressNameTable(root=root, public=public, private=private)
        # Login info
        self.__login_table = LoginTable(root=root, public=public, private=private)
        self.__active_table = ActiveTable(root=root, public=public, private=private)
        # ISP
        self.__station_table = StationTable(root=root, public=public, private=private)

    def show_info(self):
        # Entity
        self.__private_table.show_info()
        self.__meta_table.show_info()
        self.__document_table.show_info()
        self.__device_table.show_info()
        self.__user_table.show_info()
        self.__group_table.show_info()
        self.__msg_key_table.show_info()
        # Message
        self.__message_table.show_info()
        # # ANS
        # self.__ans_table.show_info()
        # Login info
        self.__login_table.show_info()
        self.__active_table.show_info()
        # ISP
        self.__station_table.show_info()

    """
        Private Key file for Users
        ~~~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/private/{ADDRESS}/secret.js'
        file path: '.dim/private/{ADDRESS}/secret_keys.js'
    """

    # Override
    def save_private_key(self, key: PrivateKey, user: ID, key_type: str = 'M') -> bool:
        return self.__private_table.save_private_key(key=key, user=user, key_type=key_type)

    # Override
    def private_keys_for_decryption(self, user: ID) -> List[DecryptKey]:
        return self.__private_table.private_keys_for_decryption(user=user)

    # Override
    def private_key_for_signature(self, user: ID) -> Optional[SignKey]:
        return self.__private_table.private_key_for_signature(user=user)

    # Override
    def private_key_for_visa_signature(self, user: ID) -> Optional[SignKey]:
        return self.__private_table.private_key_for_visa_signature(user=user)

    """
        Meta file for entities
        ~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/meta.js'
        redis key: 'mkm.meta.{ID}'
    """

    # Override
    def save_meta(self, meta: Meta, identifier: ID) -> bool:
        if not Meta.match_id(meta=meta, identifier=identifier):
            raise AssertionError('meta not match ID: %s' % identifier)
        return self.__meta_table.save_meta(meta=meta, identifier=identifier)

    # Override
    def meta(self, identifier: ID) -> Optional[Meta]:
        return self.__meta_table.meta(identifier=identifier)

    """
        Document for Accounts
        ~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/public/{ADDRESS}/profile.js'
        redis key: 'mkm.document.{ID}'
        redis key: 'mkm.docs.keys'
    """

    # Override
    def save_document(self, document: Document) -> bool:
        # check with meta first
        meta = self.meta(identifier=document.identifier)
        assert meta is not None, 'meta not exists: %s' % document
        # check document valid before saving it
        if document.valid or document.verify(public_key=meta.key):
            return self.__document_table.save_document(document=document)

    # Override
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

    # Override
    def local_users(self) -> List[ID]:
        return self.__user_table.local_users()

    # Override
    def save_local_users(self, users: List[ID]) -> bool:
        return self.__user_table.save_local_users(users=users)

    # Override
    def add_user(self, user: ID) -> bool:
        return self.__user_table.add_user(user=user)

    # Override
    def remove_user(self, user: ID) -> bool:
        return self.__user_table.remove_user(user=user)

    # Override
    def current_user(self) -> Optional[ID]:
        return self.__user_table.current_user()

    # Override
    def set_current_user(self, user: ID) -> bool:
        return self.__user_table.set_current_user(user=user)

    # Override
    def save_contacts(self, contacts: List[ID], user: ID) -> bool:
        return self.__user_table.save_contacts(contacts=contacts, user=user)

    # Override
    def contacts(self, user: ID) -> List[ID]:
        return self.__user_table.contacts(user=user)

    # Override
    def add_contact(self, contact: ID, user: ID) -> bool:
        return self.__user_table.add_contact(contact=contact, user=user)

    # Override
    def remove_contact(self, contact: ID, user: ID) -> bool:
        return self.__user_table.remove_contact(contact=contact, user=user)

    """
        Stored Contacts for User
        ~~~~~~~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/contacts_stored.js'
        redis key: 'mkm.user.{ID}.cmd.contacts'
    """

    # Override
    def save_contacts_command(self, content: Command, identifier: ID) -> bool:
        return self.__user_table.save_contacts_command(content=content, identifier=identifier)

    # Override
    def contacts_command(self, identifier: ID) -> Optional[Command]:
        return self.__user_table.contacts_command(identifier=identifier)

    """
        Block-list of User
        ~~~~~~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/block_stored.js'
        redis key: 'mkm.user.{ID}.cmd.block'
    """

    def save_block_command(self, content: BlockCommand, identifier: ID) -> bool:
        return self.__user_table.save_block_command(content=content, identifier=identifier)

    def block_command(self, identifier: ID) -> BlockCommand:
        return self.__user_table.block_command(identifier=identifier)

    def is_blocked(self, receiver: ID, sender: ID, group: ID = None) -> bool:
        cmd = self.block_command(identifier=receiver)
        if cmd is None:
            return False
        array = cmd.block_list
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

    def save_mute_command(self, content: MuteCommand, identifier: ID) -> bool:
        return self.__user_table.save_mute_command(content=content, identifier=identifier)

    def mute_command(self, identifier: ID) -> MuteCommand:
        return self.__user_table.mute_command(identifier=identifier)

    def is_muted(self, receiver: ID, sender: ID, group: ID = None) -> bool:
        cmd = self.mute_command(identifier=receiver)
        if cmd is None:
            return False
        array = cmd.mute_list
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

    def device_tokens(self, identifier: ID) -> List[str]:
        """ Tokens for APNs """
        return self.__device_table.device_tokens(identifier=identifier)

    """
        Group members
        ~~~~~~~~~~~~~

        file path: '.dim/protected/{ADDRESS}/members.txt'
        redis key: 'mkm.group.{ID}.members'
    """

    # Override
    def founder(self, group: ID) -> Optional[ID]:
        return self.__group_table.founder(group=group)

    # Override
    def owner(self, group: ID) -> Optional[ID]:
        return self.__group_table.owner(group=group)

    # Override
    def members(self, group: ID) -> List[ID]:
        return self.__group_table.members(group=group)

    # Override
    def save_members(self, members: List[ID], group: ID) -> bool:
        return self.__group_table.save_members(members=members, group=group)

    # Override
    def add_member(self, member: ID, group: ID) -> bool:
        return self.__group_table.add_member(member=member, group=group)

    # Override
    def remove_member(self, member: ID, group: ID) -> bool:
        return self.__group_table.remove_member(member=member, group=group)

    # Override
    def remove_group(self, group: ID) -> bool:
        return self.__group_table.remove_group(group=group)

    # Override
    def assistants(self, group: ID) -> List[ID]:
        return self.__group_table.assistants(group=group)

    # Override
    def save_assistants(self, assistants: List[ID], group: ID) -> bool:
        return self.__group_table.save_assistants(assistants=assistants, group=group)

    """
        Reliable message for Receivers
        ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

        redis key: 'dkd.msg.{ID}.{sig}'
        redis key: 'dkd.msg.{ID}.messages'
    """

    # Override
    def reliable_messages(self, receiver: ID, start: int = 0, limit: int = 1024) -> Tuple[List[ReliableMessage], int]:
        return self.__message_table.reliable_messages(receiver=receiver)

    # Override
    def cache_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        return self.__message_table.cache_reliable_message(msg=msg, receiver=receiver)

    # Override
    def remove_reliable_message(self, msg: ReliableMessage, receiver: ID) -> bool:
        return self.__message_table.remove_reliable_message(msg=msg, receiver=receiver)

    """
        Message Keys
        ~~~~~~~~~~~~

        redis key: 'dkd.key.{sender}'
    """

    # Override
    def cipher_key(self, sender: ID, receiver: ID, generate: bool = False) -> Optional[SymmetricKey]:
        return self.__msg_key_table.cipher_key(sender=sender, receiver=receiver, generate=generate)

    # Override
    def cache_cipher_key(self, key: SymmetricKey, sender: ID, receiver: ID):
        return self.__msg_key_table.cache_cipher_key(key=key, sender=sender, receiver=receiver)

    # """
    #     Address Name Service
    #     ~~~~~~~~~~~~~~~~~~~~
    #
    #     file path: '.dim/ans.txt'
    #     redis key: 'dim.ans'
    # """
    #
    # def ans_save_record(self, name: str, identifier: ID) -> bool:
    #     return self.__ans_table.save_record(name=name, identifier=identifier)
    #
    # def ans_record(self, name: str) -> ID:
    #     return self.__ans_table.record(name=name)
    #
    # def ans_names(self, identifier: ID) -> Set[str]:
    #     return self.__ans_table.names(identifier=identifier)

    """
        Login Info
        ~~~~~~~~~~

        redis key: 'mkm.user.{ID}.login'
    """

    # Override
    def login_command_message(self, user: ID) -> Tuple[Optional[LoginCommand], Optional[ReliableMessage]]:
        return self.__login_table.login_command_message(user=user)

    # Override
    def save_login_command_message(self, user: ID, content: LoginCommand, msg: ReliableMessage) -> bool:
        return self.__login_table.save_login_command_message(user=user, content=content, msg=msg)

    def login_command(self, user: ID) -> Optional[LoginCommand]:
        return self.__login_table.login_command(user=user)

    def login_message(self, user: ID) -> Optional[ReliableMessage]:
        return self.__login_table.login_message(user=user)

    #
    #   Active DBI
    #

    def clear_socket_addresses(self):
        """ clear before station start """
        self.__active_table.clear_socket_addresses()

    def active_users(self) -> Set[ID]:
        return self.__active_table.active_users()

    def add_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        return self.__active_table.add_socket_address(identifier=identifier, address=address)

    def remove_socket_address(self, identifier: ID, address: Tuple[str, int]) -> Set[Tuple[str, int]]:
        return self.__active_table.remove_socket_address(identifier=identifier, address=address)

    #
    #   Provider DBI
    #

    # Override
    def all_providers(self) -> List[ProviderInfo]:
        """ get list of (SP_ID, chosen) """
        return self.__station_table.all_providers()

    # Override
    def add_provider(self, identifier: ID, chosen: int = 0) -> bool:
        return self.__station_table.add_provider(identifier=identifier, chosen=chosen)

    # Override
    def update_provider(self, identifier: ID, chosen: int) -> bool:
        return self.__station_table.update_provider(identifier=identifier, chosen=chosen)

    # Override
    def remove_provider(self, identifier: ID) -> bool:
        return self.__station_table.remove_provider(identifier=identifier)

    # Override
    def all_stations(self, provider: ID) -> List[StationInfo]:
        """ get list of (host, port, SP_ID, chosen) """
        return self.__station_table.all_stations(provider=provider)

    # Override
    def add_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = 0) -> bool:
        return self.__station_table.add_station(identifier=identifier, host=host, port=port,
                                                provider=provider, chosen=chosen)

    # Override
    def update_station(self, identifier: Optional[ID], host: str, port: int, provider: ID, chosen: int = None) -> bool:
        return self.__station_table.update_station(identifier=identifier, host=host, port=port,
                                                   provider=provider, chosen=chosen)

    # Override
    def remove_station(self, host: str, port: int, provider: ID) -> bool:
        return self.__station_table.remove_station(host=host, port=port, provider=provider)

    # Override
    def remove_stations(self, provider: ID) -> bool:
        return self.__station_table.remove_stations(provider=provider)
