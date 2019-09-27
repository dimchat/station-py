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

from .utils import base64_encode, base64_decode
from .utils import hex_encode, hex_decode
from .utils import sha1
from .utils import Log

from .database import Storage, Database

from .server import ApplePushNotificationService, IAPNsDelegate
from .server import Session, SessionServer
from .server import Server

from .robot import Connection, IConnectionDelegate
from .robot import Robot

from .mars import NetMsgHead, NetMsg

from .ans import AddressNameService
from .facebook import Facebook
from .keystore import KeyStore
from .messenger import Messenger


__all__ = [
    #
    #  Utils
    #
    'base64_encode', 'base64_decode',
    'hex_encode', 'hex_decode',
    'sha1',
    'Log',

    #
    #  Database module
    #
    'Storage',
    'Database',

    #
    #  Server module
    #
    'ApplePushNotificationService', 'IAPNsDelegate',
    'Session', 'SessionServer',
    'Server',

    #
    #  Robot module
    #
    'Connection', 'IConnectionDelegate',
    'Robot',

    #
    #  Mars for data packing
    #
    'NetMsgHead', 'NetMsg',

    #
    #  Common libs
    #
    'AddressNameService',
    'Facebook',
    'KeyStore',
    'Messenger',
]
