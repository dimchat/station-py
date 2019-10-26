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

    handshake protocol
"""

from dimp import ID
from dimp import Content
from dimp import Command, HandshakeCommand

from .cpu import CPU


class HandshakeCommandProcessor(CPU):

    def process(self, cmd: Command, sender: ID) -> Content:
        # set/update session in session server with new session key
        client_address = self.request_handler.client_address
        self.info('handshake with client %s, %s' % (client_address, sender))
        if cmd is None:
            session_key = None
        else:
            assert isinstance(cmd, HandshakeCommand)
            session_key = cmd.session
        session = self.request_handler.current_session(identifier=sender)
        if session_key == session.session_key:
            # session verified success
            session.valid = True
            session.active = True
            nickname = self.facebook.nickname(identifier=sender)
            self.info('handshake accepted %s %s %s, %s' % (nickname, client_address, sender, session_key))
            self.monitor.report(message='User %s logged in %s %s' % (nickname, client_address, sender))
            # add the new guest for checking offline messages
            self.receptionist.add_guest(identifier=sender)
            return HandshakeCommand.success()
        else:
            # session key not match, ask client to sign it with the new session key
            return HandshakeCommand.again(session=session.session_key)
