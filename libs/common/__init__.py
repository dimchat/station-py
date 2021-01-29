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

import time
from typing import Optional

from dimp import ID, Content, ReliableMessage
from dimsdk import ReceiptCommand, LoginCommand

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
    :param node:
    :param append: whether append this station node
    :return: message already traced
    """
    traces = msg.get('traces')
    if traces is None:
        # broadcast message starts from here
        traces = []
        msg['traces'] = traces
    else:
        for station in traces:
            if isinstance(station, str):
                if node == station:
                    return True
            elif isinstance(station, dict):
                if node == station.get('ID'):
                    return True
            else:
                raise TypeError('traces node error: %s' % station)
    if append:
        traces.append(str(node))


def roaming_station(db: Database, user: ID, cmd: LoginCommand = None, msg: ReliableMessage = None) -> Optional[ID]:
    old = db.login_command(identifier=user)
    # 1. check time with stored command
    if old is not None and cmd is not None:
        old_time = old.time
        if old_time is None:
            old_time = 0
        new_time = cmd.time
        if new_time is None:
            new_time = 0
        if new_time <= old_time:
            # expired command, drop it
            cmd = None
    # 2. store new command
    if cmd is None:
        cmd = old
    else:
        db.save_login(cmd=cmd, msg=msg)
    # 3. get roaming station ID
    if cmd is not None:
        station = cmd.station
        last_time = cmd.time
        if isinstance(station, dict) and isinstance(last_time, int):
            # check time expires
            if (time.time() - last_time) < (3600 * 24 * 7):
                return ID.parse(identifier=station.get('ID'))


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

    'msg_receipt', 'msg_traced', 'roaming_station',
]
