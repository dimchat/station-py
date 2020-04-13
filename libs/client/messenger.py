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
from dimp import GroupCommand
from dimsdk import HandshakeCommand
from dimsdk import Station

from libs.common import CommonMessenger

from .facebook import ClientFacebook


class ClientMessenger(CommonMessenger):

    EXPIRES = 300  # query expires (5 minutes)

    def __init__(self):
        super().__init__()
        self.__meta_queries = {}     # ID -> time
        self.__profile_queries = {}  # ID -> time
        self.__group_queries = {}    # ID -> time

    @property
    def facebook(self) -> ClientFacebook:
        barrack = self.get_context('facebook')
        if barrack is None:
            barrack = self.barrack
            assert isinstance(barrack, ClientFacebook), 'messenger delegate error: %s' % barrack
        return barrack

    @property
    def station(self) -> Station:
        return self.get_context('station')

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
        self.__meta_queries[identifier] = now
        # query from DIM network
        cmd = MetaCommand.new(identifier=identifier)
        return self.send_command(cmd=cmd)

    def query_profile(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__profile_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__profile_queries[identifier] = now
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
        self.__group_queries[group] = now
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

    # Override
    def process_content(self, content: Content, sender: ID, msg: ReliableMessage) -> Optional[Content]:
        res = super().process_content(content=content, sender=sender, msg=msg)
        if res is None:
            # respond nothing
            return None
        if isinstance(res, HandshakeCommand):
            # urgent command
            return res
        # if isinstance(i_msg.content, ReceiptCommand):
        #     receiver = self.barrack.identifier(msg.envelope.receiver)
        #     if receiver.type == NetworkID.Station:
        #         # no need to respond receipt to station
        #         return None

        # check receiver
        receiver = self.facebook.identifier(msg.envelope.receiver)
        user = self._select(receiver=receiver)
        assert user is not None, 'receiver error: %s' % receiver
        # pack message
        i_msg = InstantMessage.new(content=res, sender=user.identifier, receiver=sender)
        # normal response
        self.send_message(msg=i_msg, callback=None, split=False)
        # DON'T respond to station directly
        return None
