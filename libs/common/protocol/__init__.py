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
from dimsdk import register_core_factories

from .handshake import HandshakeCommand, HandshakeState
from .receipt import ReceiptCommand
from .login import LoginCommand

from .block import BlockCommand
from .mute import MuteCommand
from .storage import StorageCommand

from .search import SearchCommand
from .report import ReportCommand


def register_all_factories():
    # Register core factories
    register_core_factories()

    # Handshake
    Command.register(cmd=HandshakeCommand.HANDSHAKE, factory=CommandFactoryBuilder(command_class=HandshakeCommand))
    # Receipt
    Command.register(cmd=ReceiptCommand.RECEIPT, factory=CommandFactoryBuilder(command_class=ReceiptCommand))
    # Login
    Command.register(cmd=LoginCommand.LOGIN, factory=CommandFactoryBuilder(command_class=LoginCommand))
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


register_all_factories()


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
