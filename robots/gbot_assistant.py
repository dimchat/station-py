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
from typing import Optional, List, Dict

from startrek import DeparturePriority

from dimples import EntityType, ID
from dimples import Envelope, InstantMessage, ReliableMessage
from dimples import Content, ForwardContent, GroupCommand
from dimples.client import GroupManager
from dimples.utils import Log

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.common import ReceiptCommand
from libs.client import ClientProcessor

from robots.shared import start_bot


# 'sender -> group' => keys
g_group_keys = {}


def get_group_key(sender: ID, member: ID, group: ID) -> Optional[str]:
    # TODO: get group key from database
    direction = '%s => %s' % (sender, group)
    keys = g_group_keys.get(direction)
    if keys is not None:
        return keys.get(str(member))


def update_group_keys(keys: Dict[str, str], sender: ID, group: ID):
    # TODO: save group keys into database
    direction = '%s -> %s' % (sender, group)
    g_group_keys[direction] = keys


def forward_group_message(msg: ReliableMessage) -> bool:
    receiver = msg.receiver
    key = msg.get('key')
    if key is None:
        # get key from cache
        sender = msg.sender
        group = msg.group
        key = get_group_key(sender=sender, member=receiver, group=group)
        if key is None:
            # cannot forward group message without key
            return False
        msg['key'] = key
    # wrap
    msg.pop('traces', None)
    forward = ForwardContent.create(message=msg)
    # pack and send
    env = Envelope.create(sender=bot_id, receiver=receiver)
    i_msg = InstantMessage.create(head=env, body=forward)
    i_msg['origin'] = {'sender': str(msg.sender), 'group': str(msg.group), 'type': msg.type}
    messenger.send_instant_message(msg=i_msg, priority=DeparturePriority.NORMAL)
    return True


def split_group_message(msg: ReliableMessage, members: List[ID]) -> Optional[Content]:
    """ Split group message for each member """
    messages = msg.split(members=members)
    success_list = []
    failed_list = []
    for item in messages:
        if item.delegate is None:
            item.delegate = msg.delegate
        if forward_group_message(msg=item):
            success_list.append(item.receiver)
        else:
            failed_list.append(item.receiver)
    response = ReceiptCommand.create(text='Group message delivering', msg=msg)
    if len(success_list) > 0:
        response['success'] = ID.revert(success_list)
    if len(failed_list) > 0:
        response['failed'] = ID.revert(failed_list)
        # failed to get keys for this members,
        # query from sender by invite members
        sender = msg.sender
        group = msg.receiver
        cmd = GroupCommand.invite(group=group, members=failed_list)
        messenger.send_content(sender=None, receiver=sender, content=cmd, priority=DeparturePriority.NORMAL)
    return response


def process_group_message(msg: ReliableMessage) -> Optional[ReliableMessage]:
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
    # 1. verify message
    s_msg = messenger.verify_message(msg=msg)
    if s_msg is None:
        # signature error?
        return None
    sender = msg.sender
    receiver = msg.receiver
    if not manager.contains_member(member=sender, group=receiver):
        if not manager.is_owner(member=sender, group=receiver):
            # not allow, kick it out
            cmd = GroupCommand.expel(group=receiver, member=sender)
            receiver = msg.sender
            env = Envelope.create(sender=bot_id, receiver=receiver)
            i_msg = InstantMessage.create(head=env, body=cmd)
            s_msg = messenger.encrypt_message(msg=i_msg)
            if s_msg is None:
                Log.error('failed to encrypt message: %s' % i_msg)
                # self.suspend_message(msg=i_msg)
                return None
            return messenger.sign_message(msg=s_msg)
    members = manager.members(receiver)
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
                    Log.info('key digest: %s' % keys[item])
                    continue
                m = ID.parse(identifier=item)
                if m not in members:
                    Log.info('remove non-exists member: %s' % item)
                    expel_list.append(m)
            if len(expel_list) > 0:
                # send 'expel' command to the sender
                cmd = GroupCommand.expel(group=receiver, members=expel_list)
                messenger.send_content(sender=None, receiver=sender,
                                       content=cmd, priority=DeparturePriority.NORMAL)
            # TODO: update key map
            update_group_keys(keys=keys, sender=sender, group=receiver)
        # split and forward group message,
        # respond receipt with success or failed list
        res = split_group_message(msg=msg, members=members)
    # pack response
    if res is not None:
        receiver = msg.sender
        env = Envelope.create(sender=bot_id, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=res)
        s_msg = messenger.encrypt_message(msg=i_msg)
        if s_msg is None:
            Log.error('failed to encrypt message: %s' % i_msg)
            # self.suspend_message(msg=i_msg)
            return None
        return messenger.sign_message(msg=s_msg)


class AssistantProcessor(ClientProcessor):

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # if msg.delegate is None:
        #     msg.delegate = self.messenger
        receiver = msg.receiver
        if receiver.is_user:
            # try to decrypt and process message
            return super().process_reliable_message(msg=msg)
        r_msg = process_group_message(msg=msg)
        return [] if r_msg is None else [r_msg]


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/config.ini'


if __name__ == '__main__':
    terminal = start_bot(default_config=DEFAULT_CONFIG,
                         app_name='DIM Group Assistant',
                         ans_name='assistant',
                         processor_class=AssistantProcessor)
    messenger = terminal.messenger
    facebook = messenger.facebook
    current_user = facebook.current_user
    bot_id = current_user.identifier
    assert bot_id.type == EntityType.BOT, 'bot ID error: %s' % current_user
    manager = GroupManager()
    manager.messenger = messenger
