#! /usr/bin/env python3
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
    Chat bot: 'LingLing'
    ~~~~~~~~~~~~~~~~~~~~

    Chat bot powered by Tuling
"""

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.client import Terminal, ClientMessenger

from robots.config import g_facebook, g_station
from robots.config import dims_connect
from robots.config import chat_bot, lingling_id

from etc.cfg_loader import load_user


"""
    Messenger for Chat Bot client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()
g_messenger.context['bots'] = [chat_bot('tuling')]  # chat bot


if __name__ == '__main__':

    # set current user
    g_facebook.current_user = load_user(lingling_id, facebook=g_facebook)

    # create client and connect to the station
    client = Terminal()
    dims_connect(terminal=client, messenger=g_messenger, station=g_station)
