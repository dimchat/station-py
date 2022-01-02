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
from typing import Optional, List

from startrek import DeparturePriority

from dimp import ID
from dimp import Envelope, InstantMessage, ReliableMessage
from dimp import ContentType
from dimp import Content, ForwardContent, GroupCommand
from dimsdk import ReceiptCommand

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Logging
from libs.common import SharedFacebook
from libs.client import Terminal, ClientMessenger

from robots.config import g_station
from robots.config import dims_connect

from etc.cfg_init import g_database


class AssistantMessenger(ClientMessenger, Logging):

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # check message delegate
        if msg.delegate is None:
            msg.delegate = self
        receiver = msg.receiver
        if not receiver.is_group:
            # try to decrypt and process message
            return super().process_reliable_message(msg=msg)
        elif self.__is_waiting_group(group=receiver, sender=msg.sender, msg_type=msg.type):
            # group not ready
            # save this message in a queue to wait group info response
            self.suspend_message(msg=msg)
            return []
        else:
            r_msg = self.__process_group_message(msg=msg)
            if r_msg is None:
                return []
            else:
                return [r_msg]

    def __is_waiting_group(self, group: ID, sender: ID, msg_type: int) -> bool:
        if group.is_broadcast:
            # broadcast group has no meta & members list to be updated,
            # so it's always ready
            return False
        facebook = self.facebook
        if facebook.is_waiting_meta(identifier=group):
            # NOTICE: if meta for group not found,
            #         facebook should query it from DIM network automatically
            self.info('waiting for meta of group: %s' % group)
            # raise LookupError('group meta not found: %s' % group)
            return True
        if facebook.is_empty_group(group=group):
            # NOTICE: if the group info not found, and this is not an 'invite/reset' command
            #         query group info from the sender
            if msg_type == ContentType.HISTORY:
                # FIXME: can we trust this stranger?
                #        may be we should keep this members list temporary,
                #        and send 'query' to the owner immediately.
                # TODO: check whether the members list is a full list,
                #       it should contain the group owner(owner)
                return False
            else:
                return self.query_group(group=group, users=[sender])
        elif facebook.exists_member(member=sender, group=group):
            # normal membership
            return False
        elif facebook.exists_assistant(member=sender, group=group):
            # normal membership
            return False
        elif facebook.is_owner(member=sender, group=group):
            # normal membership
            return False
        else:
            # if assistants exists, query them
            admins = facebook.assistants(identifier=group)
            # if owner found, query it too
            owner = facebook.owner(identifier=group)
            if owner is not None:
                if admins is None:
                    admins = [owner]
                elif owner not in admins:
                    admins = admins.copy()
                    admins.append(owner)
            return self.query_group(group=group, users=admins)

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
        if not self.facebook.exists_member(member=sender, group=receiver):
            if not self.facebook.is_owner(member=sender, group=receiver):
                # not allow, kick it out
                cmd = GroupCommand.expel(group=receiver, member=sender)
                sender = self.facebook.current_user.identifier
                receiver = msg.sender
                env = Envelope.create(sender=sender, receiver=receiver)
                i_msg = InstantMessage.create(head=env, body=cmd)
                s_msg = self.encrypt_message(msg=i_msg)
                if s_msg is None:
                    self.error('failed to encrypt message: %s' % i_msg)
                    self.suspend_message(msg=i_msg)
                    return None
                return self.sign_message(msg=s_msg)
        members = self.facebook.members(receiver)
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
                    g_messenger.send_content(sender=None, receiver=sender, content=cmd, priority=DeparturePriority.NORMAL)
                # update key map
                g_database.update_group_keys(keys=keys, sender=sender, group=receiver)
            # split and forward group message,
            # respond receipt with success or failed list
            res = self.__split_group_message(msg=msg, members=members)
        # pack response
        if res is not None:
            sender = self.facebook.current_user.identifier
            receiver = msg.sender
            env = Envelope.create(sender=sender, receiver=receiver)
            i_msg = InstantMessage.create(head=env, body=res)
            s_msg = self.encrypt_message(msg=i_msg)
            if s_msg is None:
                self.error('failed to encrypt message: %s' % i_msg)
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
            self.send_content(sender=None, receiver=sender, content=cmd, priority=DeparturePriority.NORMAL)
        return response

    def __forward_group_message(self, msg: ReliableMessage) -> bool:
        receiver = msg.receiver
        key = msg.get('key')
        if key is None:
            # get key from cache
            sender = msg.sender
            group = msg.group
            key = g_database.group_key(sender=sender, member=receiver, group=group)
            if key is None:
                # cannot forward group message without key
                return False
            msg['key'] = key
        # wrap
        msg.pop('traces', None)
        forward = ForwardContent(message=msg)
        # pack and send
        sender = self.facebook.current_user.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=forward)
        i_msg['origin'] = {'sender': str(msg.sender), 'group': str(msg.group), 'type': msg.type}
        return self.send_instant_message(msg=i_msg, priority=DeparturePriority.NORMAL)


"""
    Messenger for Group Assistant robot
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = AssistantMessenger()
g_facebook = SharedFacebook()
g_facebook.messenger = g_messenger

if __name__ == '__main__':

    # set current user
    assistant = ID.parse(identifier='assistant')
    g_facebook.current_user = g_facebook.user(identifier=assistant)

    # create client and connect to the station
    client = Terminal()
    dims_connect(terminal=client, messenger=g_messenger, server=g_station)
