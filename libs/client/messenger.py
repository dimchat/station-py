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
from typing import Union

import dkd
from dimp import ID, EVERYONE
from dimp import InstantMessage, ReliableMessage
from dimp import Content, Command, MetaCommand, DocumentCommand
from dimp import GroupCommand
from dimsdk import Station, Processor

from libs.common import CommonMessenger

from .facebook import ClientFacebook


class ClientMessenger(CommonMessenger):

    EXPIRES = 600  # query expires (10 minutes)

    def __init__(self):
        super().__init__()
        # for checking duplicated queries
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

    def _create_facebook(self) -> ClientFacebook:
        return ClientFacebook()

    def _create_processor(self) -> Processor:
        from .processor import ClientProcessor
        return ClientProcessor(messenger=self)

    @property
    def station(self) -> Station:
        return self.get_context('station')

    def broadcast_content(self, content: Content) -> bool:
        return self.send_content(sender=None, receiver=EVERYONE, content=content)

    #
    #   Command
    #
    def __send_command(self, cmd: Command) -> bool:
        station = self.station
        if station is None:
            # raise ValueError('current station not set')
            return False
        return self.send_content(sender=None, receiver=station.identifier, content=cmd)

    def query_meta(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__meta_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__meta_queries[identifier] = now
        # query from DIM network
        cmd = MetaCommand(identifier=identifier)
        return self.__send_command(cmd=cmd)

    def query_profile(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__profile_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__profile_queries[identifier] = now
        # query from DIM network
        cmd = DocumentCommand(identifier=identifier)
        return self.__send_command(cmd=cmd)

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
            if self.send_content(sender=None, receiver=item, content=cmd):
                checking = True
        return checking

    #
    #   Message
    #
    def save_message(self, msg: InstantMessage) -> bool:
        # TODO: save instant message
        return True

    def suspend_message(self, msg: Union[ReliableMessage, InstantMessage]):
        if isinstance(msg, dkd.ReliableMessage):
            # TODO: save this message in a queue waiting sender's meta response
            pass
        elif isinstance(msg, dkd.InstantMessage):
            # TODO: save this message in a queue waiting receiver's meta response
            pass
