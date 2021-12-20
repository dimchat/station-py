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
    Command Processor for 'handshake'
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Handshake Protocol
"""

from typing import List

from dimp import ReliableMessage
from dimp import Content
from dimp import Command
from dimsdk import HandshakeCommand
from dimsdk import CommandProcessor

from ...utils import Logging


class HandshakeCommandProcessor(CommandProcessor, Logging):

    # Override
    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, HandshakeCommand), 'command error: %s' % cmd
        message = cmd.message
        session = cmd.session
        sender = msg.sender
        self.info('received "handshake": %s, %s, %s' % (sender, message, session))
        server = self.messenger.server
        # from ..network import Server
        # assert isinstance(server, Server), 'server error: %s' % server
        if server is None:
            # FIXME: why?
            self.error(msg='!!! server stopped? ignore handshake: %s' % sender)
            return []
        if server.identifier != sender:
            self.error(msg='!!! ignore error handshake from this sender: %s, %s' % (sender, server))
            return []
        if 'DIM?' == message:
            # S -> C: station ask client to handshake again
            self.info('handshake again, session key: %s' % session)
            server.handshake(session_key=session)
        elif 'DIM!' == message:
            # S -> C: handshake accepted by station
            self.info('handshake success!')
            server.handshake_success()
        else:
            # C -> S: Hello world!
            self.error(msg='[Error] handshake command from %s: %s' % (sender, cmd))
        return []
