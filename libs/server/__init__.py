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
    Server Module
    ~~~~~~~~~~~~~

"""

from dimples.server import SessionCenter
from dimples.server import PushAlert, PushInfo, PushService, PushCenter
from dimples.server import Pusher, DefaultPusher
from dimples.server import Roamer, Deliver, Worker
from dimples.server import Dispatcher
from dimples.server import UserDeliver, BotDeliver, StationDeliver
from dimples.server import GroupDeliver, BroadcastDeliver
from dimples.server import DeliverWorker, DefaultRoamer
from dimples.server import Filter, DefaultFilter

from .cpu import *

from .session import ServerSession
from .messenger import ServerMessenger
from .packer import ServerPacker
from .processor import ServerProcessor
from .processor import ServerContentProcessorCreator


__all__ = [

    #
    #   CPU
    #
    'HandshakeCommandProcessor', 'LoginCommandProcessor',
    'DocumentCommandProcessor', 'ReceiptCommandProcessor',

    'MuteCommandProcessor', 'BlockCommandProcessor',
    'ReportCommandProcessor',

    # Session
    'ServerSession', 'SessionCenter',  # 'SessionPool',

    # Push Notification
    'PushAlert', 'PushInfo', 'PushService', 'PushCenter',
    'Pusher', 'DefaultPusher',

    # Deliver
    'Roamer', 'Deliver', 'Worker',
    'Dispatcher',
    'UserDeliver', 'BotDeliver', 'StationDeliver',
    'GroupDeliver', 'BroadcastDeliver',
    'DeliverWorker', 'DefaultRoamer',
    'Filter', 'DefaultFilter',

    'ServerMessenger',
    'ServerPacker',
    'ServerProcessor',
    'ServerContentProcessorCreator',
]
