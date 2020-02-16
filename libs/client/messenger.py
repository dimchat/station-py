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
    Messenger for client
    ~~~~~~~~~~~~~~~~~~~~

    Transform and send message
"""

import time
from typing import Optional, Union

from dimp import ID
from dimp import InstantMessage, ReliableMessage
from dimp import Content, Command, MetaCommand, ProfileCommand
from dimp import HandshakeCommand
from dimp import GroupCommand, InviteCommand, ResetCommand

from dimsdk import Messenger
from dimsdk import Station


class ClientMessenger(Messenger):

    EXPIRES = 300  # query expires (5 minutes)

    def __init__(self):
        super().__init__()
        self.__meta_queries = {}     # ID -> time
        self.__profile_queries = {}  # ID -> time
        self.__group_queries = {}    # ID -> time

    @property
    def station(self) -> Station:
        return self.get_context('station')

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
        if owner is None:
            return True

    def __check_group(self, content: Content, sender: ID) -> bool:
        """
        Check if it is a group message, and whether the group members info needs update

        :param content: message content
        :param sender:  message sender
        :return: True on updating
        """
        facebook = self.facebook
        group = facebook.identifier(content.group)
        if group is None or group.is_broadcast:
            # 1. personal message
            # 2. broadcast message
            return False
        # check meta for new group ID
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
                    admins.append(owner)
            return self.query_group(group=group, users=admins)

    #
    #   Command
    #
    def send_command(self, cmd: Command):
        station = self.station
        if station is None:
            raise ValueError('current station not set')
        return self.send_content(content=cmd, receiver=station.identifier)

    def query_meta(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__meta_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__meta_queries[identifier] = last
        # query from DIM network
        cmd = MetaCommand.new(identifier=identifier)
        return self.send_command(cmd=cmd)

    def query_profile(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__profile_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__profile_queries[identifier] = last
        # query from DIM network
        cmd = ProfileCommand.new(identifier=identifier)
        return self.send_command(cmd=cmd)

    # FIXME: separate checking for querying each user
    def query_group(self, group: ID, users: list) -> bool:
        now = time.time()
        last = self.__group_queries.get(group, 0)
        if (now - last) < self.EXPIRES:
            return False
        if len(users) == 0:
            return False
        self.__group_queries[group] = last
        # query from users
        cmd = GroupCommand.query(group=group)
        checking = False
        for item in users:
            if self.send_content(content=cmd, receiver=item):
                checking = True
        return checking

    #
    #   Message
    #
    def save_message(self, msg: InstantMessage) -> bool:
        # TODO: save instant message
        return True

    def suspend_message(self, msg: Union[ReliableMessage, InstantMessage]):
        if isinstance(msg, ReliableMessage):
            # TODO: save this message in a queue waiting sender's meta response
            pass
        elif isinstance(msg, InstantMessage):
            # TODO: save this message in a queue waiting receiver's meta response
            pass

    def process_reliable(self, msg: ReliableMessage) -> Optional[Content]:
        res = super().process_reliable(msg=msg)
        if res is None:
            # respond nothing
            return None
        if isinstance(res, HandshakeCommand):
            # urgent command
            return res
        # if isinstance(res, ReceiptCommand):
        #     receiver = self.barrack.identifier(msg.envelope.receiver)
        #     if receiver.type.is_station():
        #         # no need to respond receipt to station
        #         return None
        # normal response
        receiver = self.barrack.identifier(msg.envelope.sender)
        self.send_content(content=res, receiver=receiver)
        # DON'T respond to station directly
        return None

    def process_instant(self, msg: InstantMessage) -> Optional[Content]:
        sender = self.facebook.identifier(string=msg.envelope.sender)
        if self.__check_group(content=msg.content, sender=sender):
            # save this message in a queue to wait group meta response
            self.suspend_message(msg=msg)
            return None
        return super().process_instant(msg=msg)
