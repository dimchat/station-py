# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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

from dimsdk import Command, CommandFactoryBuilder

from dimples.common import HandshakeCommand, HandshakeState
from dimples.common import ReceiptCommand
from dimples.common import LoginCommand
from dimples.common import ReportCommand

from .mute import MuteCommand
from .block import BlockCommand
from .storage import StorageCommand

from .search import SearchCommand


def register_ext_factories():

    # Mute
    Command.register(cmd=MuteCommand.MUTE, factory=CommandFactoryBuilder(command_class=MuteCommand))
    # Block
    Command.register(cmd=BlockCommand.BLOCK, factory=CommandFactoryBuilder(command_class=BlockCommand))

    # Storage (contacts, private_key)
    factory = CommandFactoryBuilder(command_class=StorageCommand)
    Command.register(cmd=StorageCommand.STORAGE, factory=factory)
    Command.register(cmd=StorageCommand.CONTACTS, factory=factory)
    Command.register(cmd=StorageCommand.PRIVATE_KEY, factory=factory)

    # Search
    Command.register(cmd=SearchCommand.SEARCH, factory=CommandFactoryBuilder(command_class=SearchCommand))
    Command.register(cmd=SearchCommand.ONLINE_USERS, factory=CommandFactoryBuilder(command_class=SearchCommand))
    # Report
    Command.register(cmd=ReportCommand.REPORT, factory=CommandFactoryBuilder(command_class=ReportCommand))
    Command.register(cmd='broadcast', factory=CommandFactoryBuilder(command_class=ReportCommand))
    Command.register(cmd=ReportCommand.ONLINE, factory=CommandFactoryBuilder(command_class=ReportCommand))
    Command.register(cmd=ReportCommand.OFFLINE, factory=CommandFactoryBuilder(command_class=ReportCommand))


register_ext_factories()


__all__ = [

    'HandshakeCommand', 'HandshakeState',
    'ReceiptCommand',
    'LoginCommand',

    'BlockCommand',
    'MuteCommand',
    'StorageCommand',

    'SearchCommand',
    'ReportCommand',
]
