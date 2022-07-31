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

from dimsdk import ID, Content, ReliableMessage

from ..database.redis.message import is_broadcast_message

from .protocol import *
from .cpu import *

from .notification import NotificationNames
from .session import BaseSession

from .ans import AddressNameServer

from .keycache import KeyCache
from .facebook import CommonFacebook, SharedFacebook
from .messenger import CommonMessenger, MessengerDelegate
from .packer import CommonPacker
from .processor import CommonProcessor, CommonContentProcessorCreator


def msg_receipt(msg: ReliableMessage, text: str) -> Content:
    """
    Create receipt for received message

    :param msg:  message received
    :param text: response
    :return: ReceiptCommand
    """
    cmd = ReceiptCommand(message=text)
    for key in ['sender', 'receiver', 'time', 'group', 'signature']:
        value = msg.get(key)
        if value is not None:
            cmd[key] = value
    return cmd


def msg_traced(msg: ReliableMessage, node: ID, append: bool = False) -> bool:
    """
    Check whether station node already traced

    :param msg: network message
    :param node: station ID
    :param append: whether append this station node
    :return: message already traced
    """
    is_traced = False
    traces = msg.get('traces')
    if traces is not None:
        for station in traces:
            if isinstance(station, str):
                if node == station:
                    is_traced = True
                    break
            elif isinstance(station, dict):
                if node == station.get('ID'):
                    is_traced = True
                    break
            else:
                raise TypeError('traces node error: %s' % station)
    if append:
        if traces is None:
            # start from here
            traces = [str(node)]
        elif is_broadcast_message(msg=msg):
            # only append once for broadcast message
            if not is_traced:
                traces.append(str(node))
        else:
            # just append
            traces.append(str(node))
        msg['traces'] = traces
    return is_traced


__all__ = [

    #
    #   Protocol
    #
    'HandshakeCommand', 'HandshakeState',
    'ReceiptCommand', 'LoginCommand',
    'BlockCommand', 'MuteCommand', 'StorageCommand',
    'SearchCommand', 'ReportCommand',

    #
    #   CPU
    #
    'FileContentProcessor',
    'ReceiptCommandProcessor',
    'MuteCommandProcessor',
    'BlockCommandProcessor',
    'StorageCommandProcessor',

    #
    #   Common libs
    #
    'NotificationNames',
    'BaseSession',
    'AddressNameServer',

    'KeyCache', 'CommonFacebook', 'SharedFacebook',
    'CommonMessenger', 'CommonPacker', 'CommonProcessor',
    'CommonContentProcessorCreator',
    'MessengerDelegate',

    'msg_receipt', 'msg_traced', 'is_broadcast_message',
]
