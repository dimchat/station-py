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


class HandshakeCommandProcessor(CommandProcessor):

    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, HandshakeCommand), 'command error: %s' % cmd
        message = cmd.message
        if 'DIM?' == message:
            # station ask client to handshake again
            return [HandshakeCommand.restart(session=cmd.session)]
        elif 'DIM!' == message:
            # handshake accepted by station
            server = self.messenger.server
            server.handshake_success()
            return []
        else:
            print('[Error] handshake command from %s: %s' % (msg.sender, cmd))
            return []


# register
CommandProcessor.register(command=Command.HANDSHAKE, cpu=HandshakeCommandProcessor())
