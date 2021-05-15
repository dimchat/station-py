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

import weakref
from typing import Optional

from dimp import ID, EVERYONE
from dimp import Command
from dimp import Transceiver
from dimsdk import LoginCommand, Station

from ..common import CommonMessenger, CommonFacebook, SharedFacebook

from .network import Terminal, Server, ServerDelegate


class ClientMessenger(CommonMessenger, ServerDelegate):

    def __init__(self):
        super().__init__()
        self.__terminal: Optional[weakref.ReferenceType] = None
        # for checking duplicated queries
        self.__meta_queries = {}      # ID -> time
        self.__document_queries = {}  # ID -> time
        self.__group_queries = {}     # ID -> time

    def _create_facebook(self) -> CommonFacebook:
        facebook = SharedFacebook()
        facebook.messenger = self
        return facebook

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
        client = self.terminal
        if client is not None:
            return client.server

    #
    #   Sending command
    #
    def _send_command(self, cmd: Command, receiver: Optional[ID] = None) -> bool:
        if receiver is None:
            station = self.server
            if station is None:
                # raise ValueError('current station not set')
                return False
            else:
                receiver = station.identifier
        return self.send_content(sender=None, receiver=receiver, content=cmd)

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
        return self.send_content(sender=user.identifier, receiver=EVERYONE, content=login)
