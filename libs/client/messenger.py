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
from typing import Optional, List

from startrek import DeparturePriority

from dimp import NetworkType
from dimp import ID, EVERYONE
from dimp import Command
from dimp import Transceiver
from dimsdk import LoginCommand

from ..common import CommonMessenger, CommonFacebook, SharedFacebook

from .network import Terminal, Server


class ClientMessenger(CommonMessenger):

    def __init__(self):
        super().__init__()
        self.__terminal: Optional[weakref.ReferenceType] = None
        self.__last_login = 0

    def _create_facebook(self) -> CommonFacebook:
        facebook = SharedFacebook()
        facebook.messenger = self
        return facebook

    # Override
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
    def send_command(self, cmd: Command, priority: int, receiver: Optional[ID] = None) -> bool:
        if receiver is None:
            station = self.server
            if station is None:
                # raise ValueError('current station not set')
                return False
            else:
                receiver = station.identifier
        return self.send_content(content=cmd, priority=priority, receiver=receiver)

    # Override
    def handshake_accepted(self, identifier: ID, client_address: tuple = None):
        self._broadcast_login(identifier=identifier)

    def _broadcast_login(self, identifier: ID = None):
        if identifier is None:
            user = self.facebook.current_user
            assert user is not None, 'current user not set'
            identifier = user.identifier
        if identifier.type == NetworkType.STATION:
            # the current user is a station,
            # it would not login to another station.
            return None
        self.__last_login = int(time.time())
        # TODO: post current document to station
        # TODO: post contacts(encrypted) to station
        # broadcast login command
        login = LoginCommand(identifier=identifier)
        login.agent = 'DIMP/0.4 (Server; Linux; en-US) DIMCoreKit/0.9 (Terminal) DIM-by-GSP/1.0'
        login.station = self.server
        return self.send_content(content=login, priority=DeparturePriority.NORMAL, sender=identifier, receiver=EVERYONE)

    # Override
    def process_package(self, data: bytes) -> List[bytes]:
        responses = super().process_package(data=data)
        if responses is None or len(responses) == 0:
            # nothing response, check last login time
            now = int(time.time())
            if 0 < self.__last_login < now - 3600:
                self._broadcast_login()
        return responses
