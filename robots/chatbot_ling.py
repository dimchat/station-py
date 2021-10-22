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

from dimp import ID
from dimp import ContentType
from dimsdk import ContentProcessor

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.client import ChatTextContentProcessor
from libs.client import Terminal, ClientMessenger

from robots.nlp import chat_bots
from robots.config import g_station
from robots.config import dims_connect


bots = chat_bots(names=['tuling'])  # chat bot
ContentProcessor.register(content_type=ContentType.TEXT, cpu=ChatTextContentProcessor(bots=bots))


"""
    Messenger for Chat Bot client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()
g_facebook = g_messenger.facebook

if __name__ == '__main__':

    # set current user
    bot_id = 'lingling@2PemMVAvxpuVZw2SYwwo11iBBEBb7gCvDHa'  # chat bot: Tuling
    g_facebook.current_user = g_facebook.user(identifier=ID.parse(identifier=bot_id))

    # create client and connect to the station
    client = Terminal()
    dims_connect(terminal=client, messenger=g_messenger, server=g_station)
