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
from dimp import InstantMessage
from dimp import Content
from dimp import Command, HandshakeCommand
from dimsdk import CommandProcessor


class HandshakeCommandProcessor(CommandProcessor):

    def __init__(self, context: dict):
        super().__init__(context=context)
        self.session_server = self.context['session_server']
        self.request_handler = self.context['request_handler']
        self.monitor = self.context['monitor']
        self.receptionist = self.context['receptionist']

    def __offer(self, sender: ID, session_key: str=None) -> Content:
        # TODO: get session
        # set/update session in session server with new session key
        client_address = self.request_handler.client_address
        self.info('handshake with client %s, %s' % (client_address, sender))
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
        pass

    @staticmethod
    def __ask(session_key: str) -> Content:
        # handshake again
        return HandshakeCommand.restart(session=session_key)

    def __success(self) -> Content:
        # handshake accepted
        # TODO: report 'login'
        pass

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: InstantMessage) -> Content:
        if type(self) != HandshakeCommandProcessor:
            raise AssertionError('override me!')
        assert isinstance(content, HandshakeCommand), 'command error: %s' % content
        message = content.message
        if 'DIM!' == message:
            # S -> C
            return self.__success()
        elif 'DIM?' == message:
            # S -> C
            return self.__ask(session_key=content.session)
        else:
            # C -> S: Hello world!
            return self.__offer(session_key=content.session, sender=sender)


# register
CommandProcessor.register(command=Command.HANDSHAKE, processor_class=HandshakeCommandProcessor)
