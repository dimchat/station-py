# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Common extensions for MessageProcessor
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""

import traceback
from typing import Optional

from dimp import ID
from dimp import Content, ReliableMessage
from dimp import InviteCommand, ResetCommand
from dimsdk import MessageProcessor

from .utils import Log
from .facebook import CommonFacebook
from .messenger import CommonMessenger


class CommandProcessor(MessageProcessor):

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    @property
    def facebook(self) -> CommonFacebook:
        return self.messenger.facebook

    def __is_empty(self, group: ID) -> bool:
        """
        Check whether group info empty (lost)

        :param group: group ID
        :return: True on members, owner not found
        """
        facebook = self.facebook
        members = facebook.members(identifier=group)
        if members is None or len(members) == 0:
            return True
        owner = facebook.owner(identifier=group)
        return owner is None

    def __is_waiting_group(self, content: Content, sender: ID) -> bool:
        """
        Check if it is a group message, and whether the group members info needs update

        :param content: message content
        :param sender:  message sender
        :return: True on updating
        """
        group = content.group
        if group is None or group.is_broadcast:
            # 1. personal message
            # 2. broadcast message
            return False
        # check meta for new group ID
        facebook = self.facebook
        meta = facebook.meta(identifier=group)
        if meta is None:
            # NOTICE: if meta for group not found,
            #         facebook should query it from DIM network automatically
            # TODO: insert the message to a temporary queue to wait meta
            # raise LookupError('group meta not found: %s' % group)
            return True
        # query group info
        if self.__is_empty(group=group):
            # NOTICE: if the group info not found, and this is not an 'invite' command
            #         query group info from the sender
            if isinstance(content, InviteCommand) or isinstance(content, ResetCommand):
                # FIXME: can we trust this stranger?
                #        may be we should keep this members list temporary,
                #        and send 'query' to the owner immediately.
                # TODO: check whether the members list is a full list,
                #       it should contain the group owner(owner)
                return False
            else:
                return self.messenger.query_group(group=group, users=[sender])
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
                    admins.append(owner)
            return self.messenger.query_group(group=group, users=admins)

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> Optional[Content]:
        sender = r_msg.sender
        if self.__is_waiting_group(content=content, sender=sender):
            # save this message in a queue to wait group meta response
            group = content.group
            r_msg['waiting'] = group
            self.messenger.suspend_message(msg=r_msg)
            return None
        try:
            return super().process_content(content=content, r_msg=r_msg)
        except LookupError as e:
            error = '%s' % e
            if error.find('failed to get meta') >= 0:
                # TODO: suspend message to wait meta
                # self.suspend_message(msg=msg)
                self.info(error)
            else:
                traceback.print_exc()
