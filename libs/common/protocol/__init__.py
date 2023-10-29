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

from dimples import Command, CommandFactoryBuilder
from dimples import HandshakeCommand, HandshakeState
from dimples import ReceiptCommand
from dimples import LoginCommand
from dimples import ReportCommand
from dimples import BlockCommand
from dimples import MuteCommand

from .apns import PushCommand
from .apns import PushAlert, PushInfo, PushItem


def register_ext_factories():

    # APNs
    Command.register(cmd=PushCommand.PUSH, factory=CommandFactoryBuilder(command_class=PushCommand))

    # Report extra
    factory = CommandFactoryBuilder(command_class=ReportCommand)
    Command.register(cmd='broadcast', factory=factory)
    Command.register(cmd=ReportCommand.ONLINE, factory=factory)
    Command.register(cmd=ReportCommand.OFFLINE, factory=factory)


register_ext_factories()


__all__ = [

    'PushCommand',
    'PushAlert', 'PushInfo', 'PushItem',

    'HandshakeCommand', 'HandshakeState',
    'ReceiptCommand',
    'LoginCommand',
    'ReportCommand',

    'BlockCommand',
    'MuteCommand',

]
