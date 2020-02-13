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

from typing import Optional, Union

from dimp import ID
from dimp import InstantMessage, ReliableMessage
from dimp import Content, Command, MetaCommand
from dimp import HandshakeCommand

from dimsdk import Messenger
from dimsdk import Station


class ClientMessenger(Messenger):

    def __init__(self):
        super().__init__()

    @property
    def station(self) -> Station:
        return self.get_context('station')

    #
    #   Command
    #
    def send_command(self, cmd: Command):
        station = self.station
        if station is None:
            raise ValueError('current station not set')
        return self.send_content(content=cmd, receiver=station.identifier)

    def query_meta(self, identifier: ID) -> bool:
        cmd = MetaCommand.new(identifier=identifier)
        return self.send_command(cmd=cmd)

    #
    #   Message
    #
    def save_message(self, msg: InstantMessage) -> bool:
        # TODO: save instant message
        return True

    def suspend_message(self, msg: Union[ReliableMessage, InstantMessage]):
        if isinstance(msg, ReliableMessage):
            # TODO: save this message in a queue waiting sender's meta response
            pass
        elif isinstance(msg, InstantMessage):
            # TODO: save this message in a queue waiting receiver's meta response
            pass

    def process_message(self, msg: ReliableMessage) -> Optional[Content]:
        res = super().process_message(msg=msg)
        if res is None:
            # respond nothing
            return None
        if isinstance(res, HandshakeCommand):
            # urgent command
            return res
        # if isinstance(res, ReceiptCommand):
        #     receiver = self.barrack.identifier(msg.envelope.receiver)
        #     if receiver.type.is_station():
        #         # no need to respond receipt to station
        #         return None
        # normal response
        receiver = self.barrack.identifier(msg.envelope.sender)
        self.send_content(content=res, receiver=receiver)
        # DON'T respond to station directly
        return None
