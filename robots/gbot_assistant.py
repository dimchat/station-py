#! /usr/bin/env python3
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
    Group bot: 'assistant'
    ~~~~~~~~~~~~~~~~~~~~~~

    Bot for collecting and responding group member list
"""

import sys
import os
import time
from typing import Optional, List

from dimp import ID
from dimp import Envelope, InstantMessage, ReliableMessage
from dimp import Content, ForwardContent, GroupCommand
from dimsdk import ReceiptCommand

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.common import Storage

from libs.client import Terminal, ClientMessenger

from robots.config import g_facebook, g_keystore, g_database, g_station
from robots.config import dims_connect
from robots.config import chat_bot, group_assistants

from etc.cfg_loader import load_user


def current_time() -> str:
    time_array = time.localtime()
    return time.strftime('%Y-%m-%d %H:%M:%S', time_array)


class GroupKeyCache(Storage):

    def __init__(self):
        super().__init__()
        self.__cache = {}  # group => (sender => (member => key str))

    # path: '/data/.dim/protected/{GROUP_ADDRESS}/group-keys-{SENDER_ADDRESS).json'
    @staticmethod
    def __path(group: ID, sender: ID) -> str:
        filename = 'group-keys-%s.js' % str(sender.address)
        return os.path.join(g_database.base_dir, 'protected', str(group.address), filename)

    def __load_keys(self, sender: ID, group: ID) -> dict:
        path = self.__path(group=group, sender=sender)
        self.info('Loading group keys from: %s' % path)
        return self.read_json(path=path)

    def __save_keys(self, keys: dict, sender: ID, group: ID) -> bool:
        path = self.__path(group=group, sender=sender)
        self.info('Saving group keys into: %s' % path)
        return self.write_json(container=keys, path=path)

    def update_keys(self, keys: dict, sender: ID, group: ID):
        table = self.__cache.get(group)
        if table is None:
            # no keys for this group yet
            table = {}
            self.__cache[group] = table
        key_map = table.get(sender)
        if key_map is None or key_map['digest'] is None:
            # no keys from this sender yet
            table[sender] = keys
            dirty = True
        elif key_map['digest'] != keys['digest']:
            # key changed
            table[sender] = keys
            dirty = True
        else:
            dirty = False
            # update key map with member
            for (member, key) in keys.items():
                if key is None or len(key) == 0:
                    # empty key
                    continue
                key_map[member] = key
                dirty = True
            keys = key_map
        if dirty:
            self.__save_keys(keys=keys, sender=sender, group=group)

    def get_keys(self, sender: ID, group: ID) -> dict:
        # get table for all members in this group
        table = self.__cache.get(group)
        if table is None:
            # try to load keys
            keys = self.__load_keys(sender=sender, group=group)
            if keys is None:
                keys = {}
            # cache keys
            table = {sender: keys}
            self.__cache[group] = table
        else:
            # get keys from the sender
            keys = table.get(sender)
            if keys is None:
                # try to load keys
                keys = self.__load_keys(sender=sender, group=group)
                if keys is None:
                    keys = {}
                # cache keys
                table[sender] = keys
        return keys

    def get_key(self, sender: ID, member: ID, group: ID) -> Optional[str]:
        key_map = self.get_keys(sender=sender, group=group)
        assert key_map is not None, 'key map error: %s -> %s' % (sender, group)
        key = key_map.get(member)
        if key is None:
            self.error('failed to get key for: %s (%s => %s)' % (member, sender, group))
        return key


class AssistantMessenger(ClientMessenger):

    def __init__(self):
        super().__init__()
        self.__key_cache = GroupKeyCache()

    #
    #  Log
    #
    @classmethod
    def info(cls, msg: str):
        print('[%s] Storage > %s' % (current_time(), msg))

    @classmethod
    def error(cls, msg: str):
        print('[%s] ERROR - Storage > %s' % (current_time(), msg))

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        # check message delegate
        if msg.delegate is None:
            msg.delegate = self
        receiver = msg.receiver
        if receiver.is_group:
            # FIXME: check group meta/profile
            meta = self.facebook.meta(identifier=receiver)
            if meta is None:
                self.suspend_message(msg=msg)
                self.info(msg='waiting for meta of group: %s' % receiver)
                return None
            # process group message
            return self.__process_group_message(msg=msg)
        # try to decrypt and process message
        return super().process_reliable_message(msg=msg)

    def __process_group_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        """
        Separate group message and forward them one by one

            if members not found,
                drop this message and query group info from sender;
            if 'keys' found in group message,
                update them to cache;
                remove non-exists member from 'keys
            split group message with members, forward them

        :param msg:
        :return: ReliableMessage as result
        """
        s_msg = self.verify_message(msg=msg)
        if s_msg is None:
            # signature error?
            return None
        sender = msg.sender
        receiver = msg.receiver
        if not g_facebook.exists_member(member=sender, group=receiver):
            if not g_facebook.is_owner(member=sender, group=receiver):
                # not allow, kick it out
                cmd = GroupCommand.expel(group=receiver, member=sender)
                sender = g_facebook.current_user.identifier
                receiver = msg.sender
                env = Envelope.create(sender=sender, receiver=receiver)
                i_msg = InstantMessage.create(head=env, body=cmd)
                s_msg = self.encrypt_message(msg=i_msg)
                if s_msg is None:
                    self.error(msg='failed to encrypt message: %s' % i_msg)
                    self.suspend_message(msg=i_msg)
                    return None
                return self.sign_message(msg=s_msg)
        members = g_facebook.members(receiver)
        if members is None or len(members) == 0:
            # members not found for this group,
            # query it from sender
            res = GroupCommand.query(group=receiver)
        else:
            # check 'keys'
            keys = msg.get('keys')
            if keys is not None:
                # remove non-exists members from 'keys'
                expel_list = []
                for item in keys:
                    if item == 'digest':
                        self.info('key digest: %s' % keys[item])
                        continue
                    m = ID.parse(identifier=item)
                    if m not in members:
                        self.info('remove non-exists member: %s' % item)
                        expel_list.append(m)
                if len(expel_list) > 0:
                    # send 'expel' command to the sender
                    cmd = GroupCommand.expel(group=receiver, members=expel_list)
                    g_messenger.send_content(sender=None, receiver=sender, content=cmd)
                # update key map
                self.__key_cache.update_keys(keys=keys, sender=sender, group=receiver)
            # split and forward group message,
            # respond receipt with success or failed list
            res = self.__split_group_message(msg=msg, members=members)
        # pack response
        if res is not None:
            sender = g_facebook.current_user.identifier
            receiver = msg.sender
            env = Envelope.create(sender=sender, receiver=receiver)
            i_msg = InstantMessage.create(head=env, body=res)
            s_msg = self.encrypt_message(msg=i_msg)
            if s_msg is None:
                self.error(msg='failed to encrypt message: %s' % i_msg)
                self.suspend_message(msg=i_msg)
                return None
            return self.sign_message(msg=s_msg)

    def __split_group_message(self, msg: ReliableMessage, members: List[ID]) -> Optional[Content]:
        """ Split group message for each member """
        messages = msg.split(members=members)
        success_list = []
        failed_list = []
        for item in messages:
            if item.delegate is None:
                item.delegate = msg.delegate
            if self.__forward_group_message(msg=item):
                success_list.append(item.receiver)
            else:
                failed_list.append(item.receiver)
        response = ReceiptCommand(message='Group message delivering')
        if len(success_list) > 0:
            response['success'] = ID.revert(success_list)
        if len(failed_list) > 0:
            response['failed'] = ID.revert(failed_list)
            # failed to get keys for this members,
            # query from sender by invite members
            sender = msg.sender
            group = msg.receiver
            cmd = GroupCommand.invite(group=group, members=failed_list)
            self.send_content(sender=None, receiver=sender, content=cmd)
        return response

    def __forward_group_message(self, msg: ReliableMessage) -> bool:
        receiver = msg.receiver
        key = msg.get('key')
        if key is None:
            # get key from cache
            sender = msg.sender
            group = msg.group
            key = self.__key_cache.get_key(sender=sender, member=receiver, group=group)
            if key is None:
                # cannot forward group message without key
                return False
            msg['key'] = key
        forward = ForwardContent(message=msg)
        return self.send_content(sender=None, receiver=receiver, content=forward)


"""
    Messenger for Group Assistant robot
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = AssistantMessenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore
g_messenger.context['database'] = g_database
# chat bot
g_messenger.context['bots'] = [chat_bot('tuling'), chat_bot('xiaoi')]

g_facebook.messenger = g_messenger


if __name__ == '__main__':

    # set current user
    g_facebook.current_user = load_user(group_assistants[0], facebook=g_facebook)

    # create client and connect to the station
    client = Terminal()
    dims_connect(terminal=client, messenger=g_messenger, station=g_station)
