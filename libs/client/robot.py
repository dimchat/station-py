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
    Robot Client
    ~~~~~~~~~~~~

    Simple client for Robot
"""

from mkm import EVERYONE
from dimp import ID, Station
from dimp import Content, Command, HandshakeCommand

from .connection import Connection
from .terminal import Terminal


class Robot(Terminal):

    def __init__(self, identifier: ID):
        super().__init__(identifier=identifier)
        # station connection
        self.station: Station = None
        self.session: str = None
        self.connection: Connection = None

    def __del__(self):
        self.disconnect()

    def info(self, msg: str):
        print('\r##### %s > %s' % (self.identifier.name, msg))

    def error(self, msg: str):
        print('\r!!!!! %s > %s' % (self.identifier.name, msg))

    def disconnect(self) -> bool:
        if self.connection:
            if self.messenger.delegate == self.connection:
                self.messenger.delegate = None
            self.connection.disconnect()
            self.connection = None
            return True

    def connect(self, station: Station) -> bool:
        conn = Connection()
        conn.delegate = self
        conn.connect(station=station)
        self.connection = conn
        self.station = station
        if self.messenger.delegate is None:
            self.messenger.delegate = self.connection
        return True

    # def send_message(self, msg: ReliableMessage) -> bool:
    #     # encode
    #     pack = json.dumps(msg)
    #     data = pack.encode('utf-8')
    #     # send out
    #     handler: ICompletionHandler = None
    #     return self.connection.send_package(data=data, handler=handler)

    def send_command(self, cmd: Command) -> bool:
        """ Send command to current station """
        return self.send_content(content=cmd, receiver=self.station.identifier)

    def broadcast_content(self, content: Content, receiver: ID) -> bool:
        content.group = EVERYONE
        return self.send_content(content=content, receiver=receiver)

    def process(self, cmd: Command, sender: ID) -> bool:
        """ Execute commands sent by commander """
        if super().process(cmd=cmd, sender=sender):
            return True
        if sender == self.station.identifier:
            # command from station
            command = cmd.command
            if 'handshake' == command:
                # process handshake command to login
                cmd = HandshakeCommand(cmd)
                if 'DIM!' == cmd.message:
                    self.info('handshake OK!')
                elif 'DIM?' == cmd.message:
                    self.session = cmd.session
                    self.info('handshake again with new session: %s' % cmd.session)
                    self.handshake()
                return True
        # let the subclass to process other command

    #
    #  [Handshake Protocol]
    #
    def handshake(self) -> bool:
        self.info('handshake with "%s"...' % self.station.identifier)
        cmd = HandshakeCommand.start(session=self.session)
        return self.send_command(cmd=cmd)
