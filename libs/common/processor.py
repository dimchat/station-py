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
from typing import List

from dimp import ID
from dimp import Content, InstantMessage, ReliableMessage
from dimp import ForwardContent
from dimp import InviteCommand, ResetCommand
from dimsdk import MessageProcessor

from ..utils import Logging

from .facebook import CommonFacebook
from .messenger import CommonMessenger


class CommonProcessor(MessageProcessor, Logging):

    @property
    def messenger(self) -> CommonMessenger:
        transceiver = super().messenger
        assert isinstance(transceiver, CommonMessenger), 'messenger error: %s' % transceiver
        return transceiver

    @property
    def facebook(self) -> CommonFacebook:
        return self.messenger.facebook

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
        if facebook.is_waiting_meta(identifier=group):
            # NOTICE: if meta for group not found,
            #         facebook should query it from DIM network automatically
            self.info('waiting for meta of group: %s' % group)
            # raise LookupError('group meta not found: %s' % group)
            return True
        if facebook.is_empty_group(group=group):
            # NOTICE: if the group info not found, and this is not an 'invite/reset' command
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
                    admins = admins.copy()
                    admins.append(owner)
            return self.messenger.query_group(group=group, users=admins)

    # Override
    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        messenger = self.messenger
        sender = r_msg.sender
        if self.__is_waiting_group(content=content, sender=sender):
            # group not ready
            # save this message in a queue to wait group info response
            messenger.suspend_message(msg=r_msg)
            return []
        try:
            return super().process_content(content=content, r_msg=r_msg)
        except Exception as error:
            err_msg = '%s' % error
            if err_msg.find('failed to get meta') >= 0:
                # suspend message to wait meta
                messenger.suspend_message(msg=r_msg)
                self.info(err_msg)
            else:
                traceback.print_exc()
            return []

    # Override
    def process_instant_message(self, msg: InstantMessage, r_msg: ReliableMessage) -> List[InstantMessage]:
        messenger = self.messenger
        # unwrap secret message circularly
        content = msg.content
        while isinstance(content, ForwardContent):
            assert isinstance(content, ForwardContent)
            r_msg = content.message
            s_msg = messenger.verify_message(msg=r_msg)
            if s_msg is None:
                # signature not matched
                return []
            msg = messenger.decrypt_message(msg=s_msg)
            if msg is None:
                # not for you?
                return []
            content = msg.content
        # call super to process
        responses = super().process_instant_message(msg=msg, r_msg=r_msg)
        # save instant/secret message
        if not messenger.save_message(msg=msg):
            # error
            return []
        return responses
