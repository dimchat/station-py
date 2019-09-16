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

import json
from time import sleep

from mkm import is_broadcast
from dimp import ID, Meta, Station
from dimp import Content, Command, HandshakeCommand, MetaCommand
from dimp import InstantMessage, ReliableMessage
from dimp import ICompletionHandler

from ..facebook import Facebook

from .connection import Connection
from .terminal import Terminal


class Robot(Terminal):

    def __init__(self, identifier: ID):
        super().__init__(identifier=identifier)
        # station connection
        self.station: Station = None
        self.connection: Connection = None
        self.session: str = None

    def __del__(self):
        self.disconnect()

    def disconnect(self) -> bool:
        if self.connection:
            self.connection.close()
            self.connection = None
            return True

    def connect(self, station: Station) -> bool:
        conn = Connection()
        conn.delegate = self
        conn.connect(station=station)
        self.connection = conn
        self.station = station
        return True

    def send_message(self, msg: ReliableMessage) -> bool:
        # encode
        pack = json.dumps(msg)
        data = pack.encode('utf-8')
        # send out
        handler: ICompletionHandler = None
        return self.connection.send_package(data=data, handler=handler)

    def send_content(self, content: Content, receiver: ID) -> bool:
        """ Send message content to receiver """
        # check meta
        self.check_meta(identifier=receiver)
        # check group message
        if receiver.type.is_group():
            content.group = receiver
        # create InstantMessage
        i_msg = InstantMessage.new(content=content, sender=self.identifier, receiver=receiver)
        # encrypt and sign
        r_msg = self.messenger.encrypt_sign(msg=i_msg)
        # send ReliableMessage
        return self.send_message(msg=r_msg)
        # return self.messenger.send_message(msg=i_msg)

    def send_command(self, cmd: Command) -> bool:
        """ Send command to current station """
        return self.send_content(content=cmd, receiver=self.station.identifier)

    def execute(self, cmd: Command, sender: ID) -> bool:
        """ Execute commands sent by commander """
        if super().execute(cmd=cmd, sender=sender):
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

    def check_meta(self, identifier: ID) -> Meta:
        facebook: Facebook = self.delegate
        meta = facebook.meta(identifier=identifier)
        if meta is None and not is_broadcast(identifier=identifier):
            # query meta from DIM network
            cmd = MetaCommand.query(identifier=identifier)
            self.send_command(cmd)
            # waiting for station response
            for i in range(30):
                sleep(0.5)
                meta = facebook.meta(identifier=identifier)
                if meta is not None:
                    break
        return meta

    def info(self, msg: str):
        print('\r##### %s > %s' % (self.identifier.name, msg))

    def error(self, msg: str):
        print('\r!!!!! %s > %s' % (self.identifier.name, msg))
