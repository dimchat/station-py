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

from typing import Optional

from dimp import ID
from dimp import ReliableMessage
from dimp import Content, TextContent
from dimp import Command
from dimsdk import HandshakeCommand
from dimsdk import CommandProcessor

from ..messenger import ServerMessenger
from ..session import SessionServer


g_session_server = SessionServer()


class HandshakeCommandProcessor(CommandProcessor):

    def __offer(self, sender: ID, session_key: str = None) -> Content:
        # set/update session in session server with new session key
        messenger = self.messenger
        assert isinstance(messenger, ServerMessenger), 'messenger error: %s' % messenger
        session = messenger.current_session
        if session_key == session.key:
            # session verified success
            g_session_server.update_session(session=session, identifier=sender)
            response = messenger.handshake_accepted(session=session)
            if response is None:
                response = HandshakeCommand.success()
            return response
        else:
            # session key not match, ask client to sign it with the new session key
            return HandshakeCommand.again(session=session.key)

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, HandshakeCommand), 'command error: %s' % cmd
        message = cmd.message
        if message in ['DIM?', 'DIM!']:
            # S -> C
            return TextContent(text='Handshake command error: %s' % message)
        else:
            # C -> S: Hello world!
            assert 'Hello world!' == message, 'Handshake command error: %s' % cmd
            return self.__offer(session_key=cmd.session, sender=msg.sender)


# register
CommandProcessor.register(command=Command.HANDSHAKE, cpu=HandshakeCommandProcessor())
