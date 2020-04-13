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

from abc import ABCMeta, abstractmethod
from typing import Optional

from dimp import ID
from dimp import ReliableMessage
from dimp import Content
from dimp import Command
from dimsdk import HandshakeCommand
from dimsdk import CommandProcessor


class HandshakeDelegate(metaclass=ABCMeta):

    @abstractmethod
    def handshake_success(self) -> Optional[Content]:
        """ Processed by Client """
        pass


class HandshakeCommandProcessor(CommandProcessor):

    @property
    def delegate(self) -> HandshakeDelegate:
        return self.get_context('handshake_delegate')

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: ReliableMessage) -> Content:
        assert isinstance(content, HandshakeCommand), 'command error: %s' % content
        message = content.message
        if 'DIM?' == message:
            # station ask client to handshake again
            return HandshakeCommand.restart(session=content.session)
        elif 'DIM!' == message:
            # handshake accepted by station
            return self.delegate.handshake_success()


# register
CommandProcessor.register(command=Command.HANDSHAKE, processor_class=HandshakeCommandProcessor)
