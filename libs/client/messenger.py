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
import weakref
from typing import List, Optional

from dimp import ID, EVERYONE
from dimp import Content, Command, MetaCommand, DocumentCommand, GroupCommand
from dimp import Transceiver
from dimsdk import LoginCommand, Station

from ..common import CommonMessenger

from .network import Terminal, Server, ServerDelegate
from .facebook import ClientFacebook


class ClientMessenger(CommonMessenger, ServerDelegate):

    EXPIRES = 600  # query expires (10 minutes)

    def __init__(self):
        super().__init__()
        self.__terminal: Optional[weakref.ReferenceType] = None
        # for checking duplicated queries
        self.__meta_queries = {}      # ID -> time
        self.__document_queries = {}  # ID -> time
        self.__group_queries = {}     # ID -> time

    def _create_facebook(self) -> ClientFacebook:
        return ClientFacebook()

    def _create_processor(self) -> Transceiver.Processor:
        from .processor import ClientProcessor
        return ClientProcessor(messenger=self)

    @property
    def terminal(self) -> Terminal:
        if self.__terminal is not None:
            return self.__terminal()

    @terminal.setter
    def terminal(self, client: Terminal):
        self.__terminal = weakref.ref(client)

    @property
    def server(self) -> Server:
        return self.terminal.server

    def broadcast_content(self, content: Content) -> bool:
        return self.send_content(sender=None, receiver=EVERYONE, content=content)

    #
    #   Command
    #
    def __send_command(self, cmd: Command) -> bool:
        station = self.server
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
        self.info('querying meta for %s' % identifier)
        cmd = MetaCommand(identifier=identifier)
        return self.__send_command(cmd=cmd)

    def query_document(self, identifier: ID) -> bool:
        now = time.time()
        last = self.__document_queries.get(identifier, 0)
        if (now - last) < self.EXPIRES:
            return False
        self.__document_queries[identifier] = now
        # query from DIM network
        self.info('querying document for %s' % identifier)
        cmd = DocumentCommand(identifier=identifier)
        return self.__send_command(cmd=cmd)

    # FIXME: separate checking for querying each user
    def query_group(self, group: ID, users: List[ID]) -> bool:
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
    #   Server Delegate
    #
    def handshake_accepted(self, server: Server):
        user = self.facebook.current_user
        if isinstance(user, Station):
            return None
        # post current profile to station
        # post contacts(encrypted) to station
        # broadcast login command
        login = LoginCommand(identifier=user.identifier)
        login.agent = 'DIMP/0.4 (Server; Linux; en-US) DIMCoreKit/0.9 (Terminal) DIM-by-GSP/1.0'
        login.station = self.server
        # self.messenger.broadcast_content(content=login)
        return self.send_content(sender=user.identifier, receiver=EVERYONE, content=login)
