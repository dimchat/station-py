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

from dimp import Command, DocumentCommand
from dimp.protocol import CommandFactoryBuilder

from .search import SearchCommand
from .report import ReportCommand


def register_all_processors():
    # extended document commands
    factory = CommandFactoryBuilder(command_class=DocumentCommand)
    Command.register(command='profile', factory=factory)
    Command.register(command='visa', factory=factory)
    Command.register(command='bulletin', factory=factory)
    # search
    Command.register(command=SearchCommand.SEARCH, factory=CommandFactoryBuilder(command_class=SearchCommand))
    Command.register(command=SearchCommand.ONLINE_USERS, factory=CommandFactoryBuilder(command_class=SearchCommand))
    # report
    Command.register(command=ReportCommand.REPORT, factory=CommandFactoryBuilder(command_class=ReportCommand))
    Command.register(command='broadcast', factory=CommandFactoryBuilder(command_class=ReportCommand))
    Command.register(command=ReportCommand.ONLINE, factory=CommandFactoryBuilder(command_class=ReportCommand))
    Command.register(command=ReportCommand.OFFLINE, factory=CommandFactoryBuilder(command_class=ReportCommand))


register_all_processors()


__all__ = [
    'SearchCommand',
    'ReportCommand',
]
