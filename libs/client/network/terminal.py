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
    Terminal
    ~~~~~~~~

    Local User
"""

from typing import Optional

from dimp import ID, EVERYONE
from dimp import Content, Command

from libs.common import CommonMessenger, CommonFacebook

from .server import Server


class Terminal:

    def __init__(self):
        super().__init__()
        self.__messenger = None
        # current station
        self.__server: Optional[Server] = None

    def __del__(self):
        self.stop()

    def info(self, msg: str):
        print('\r##### %s > %s' % (self.facebook.current_user, msg))

    def error(self, msg: str):
        print('\r!!!!! %s > %s' % (self.facebook.current_user, msg))

    @property
    def server(self):
        return self.__server

    def start(self, server: Server):
        server.connect()
        self.__server = server

    def stop(self):
        if self.__server is not None:
            self.__server.disconnect()

    @property
    def messenger(self) -> CommonMessenger:
        return self.__messenger

    @messenger.setter
    def messenger(self, transceiver: CommonMessenger):
        self.__messenger = transceiver

    @property
    def facebook(self) -> CommonFacebook:
        return self.messenger.facebook

    def send_command(self, cmd: Command) -> bool:
        """ Send command to current station """
        sender = self.facebook.current_user.identifier
        receiver = self.__server.identifier
        return self.messenger.send_content(sender=sender, receiver=receiver, content=cmd)

    def broadcast_content(self, content: Content, receiver: ID) -> bool:
        sender = self.facebook.current_user.identifier
        content.group = EVERYONE
        return self.messenger.send_content(sender=sender, receiver=receiver, content=content)
