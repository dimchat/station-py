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
    Common Libs
    ~~~~~~~~~~~

    Common libs for Server or Client
"""

from .protocol import SearchCommand, ReportCommand
from .cpu import *
from .network import NetMsgHead, NetMsg
from .network import WebSocket
from .database import Storage, Database

from .ans import AddressNameServer
from .notification import NotificationNames

from .keystore import KeyStore
from .facebook import CommonFacebook
from .messenger import CommonMessenger
from .packer import CommonPacker
from .processor import CommonProcessor


__all__ = [

    #
    #   Protocol
    #
    'SearchCommand', 'ReportCommand',

    #
    #   CPU
    #
    'TextContentProcessor',

    #
    #   Network
    #
    'NetMsgHead', 'NetMsg',
    'WebSocket',

    #
    #   Database module
    #
    'Storage',
    'Database',

    #
    #   Common libs
    #
    'AddressNameServer',
    'NotificationNames',

    'KeyStore', 'CommonFacebook',
    'CommonMessenger', 'CommonPacker', 'CommonProcessor',
]
