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
    Message Processor
    ~~~~~~~~~~~~~~~~~

    Message processor for Request Handler
"""

from dimp import ID
from dimp import Content, TextContent, Command, HistoryCommand
from dimp import InstantMessage

from libs.common import Log
from libs.server import Session, Server
from libs.client import Dialog

from .cmd import CPU
from .config import g_facebook, g_database, g_session_server, g_receptionist, g_monitor
from .config import station_name, chat_bot


class MessageProcessor:

    def __init__(self, request_handler):
        super().__init__()
        self.__handler = request_handler
        self.__dialog: Dialog = None
        # Command Processing Unit
        self.__cpu = CPU(request_handler=request_handler,
                         facebook=g_facebook, database=g_database, session_server=g_session_server,
                         receptionist=g_receptionist, monitor=g_monitor)
        self.__cpu.station_name = station_name

    def info(self, msg: str):
        Log.info('%s:\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s ERROR:\t%s' % (self.__class__.__name__, msg))

    @property
    def client_address(self) -> str:
        return self.__handler.client_address

    @property
    def identifier(self) -> ID:
        return self.__handler.identifier

    @property
    def station(self) -> Server:
        return self.__handler.station

    def current_session(self, identifier: ID=None) -> Session:
        return self.__handler.current_session(identifier=identifier)

    def check_session(self, identifier: ID) -> Content:
        return self.__handler.check_session(identifier=identifier)

    """
        main entrance
    """
    def process(self, msg: InstantMessage) -> Content:
        # try to decrypt message
        sender = g_facebook.identifier(msg.envelope.sender)
        content = msg.content
        if isinstance(content, Command):
            # the client is talking with station (handshake, search users, get meta/profile, ...)
            self.info('command from client %s, %s' % (self.client_address, content))
            return self.process_command(cmd=Command(content), sender=sender)
        else:
            # talk with station?
            self.info('message from client %s, %s' % (self.client_address, content))
            return self.process_dialog(content=content, sender=sender)

    def process_dialog(self, content: Content, sender: ID) -> Content:
        if self.__dialog is None:
            self.__dialog = Dialog()
            self.__dialog.bots = [chat_bot('tuling'), chat_bot('xiaoi')]
        self.info('@@@ call NLP and response to the client %s, %s' % (self.client_address, sender))
        nickname = g_facebook.nickname(identifier=sender)
        response = self.__dialog.query(content=content, sender=sender)
        if response is not None:
            assert isinstance(response, TextContent)
            assert isinstance(content, TextContent)
            question = content.text
            answer = response.text
            self.info('Dialog > %s(%s): "%s" -> "%s"' % (nickname, sender, question, answer))
            return response
        # TEST: response client with the same message here
        self.info('Dialog > message from %s(%s): %s' % (nickname, sender, content))
        return content

    def process_command(self, cmd: Command, sender: ID) -> Content:
        command = cmd.command
        # priority commands
        if command in ['handshake', 'meta', 'profile']:
            return self.__cpu.process(cmd=cmd, sender=sender)
        # check session valid
        handshake = self.check_session(identifier=sender)
        if handshake is not None:
            return handshake
        # extra commands will be processed by Command Process Units
        self.info('extra command: %s, sender: %s' % (cmd, sender))
        return self.__cpu.process(cmd=cmd, sender=sender)
