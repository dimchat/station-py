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
    Robot Config
    ~~~~~~~~~~~~

    Configuration for Robot
"""

#
#  Common Libs
#
from libs.utils import Log
from libs.client import ClientMessenger
from libs.client import Server, Terminal

#
#  Configurations
#
from etc.config import local_host, local_port

from etc.cfg_init import station_id
from etc.cfg_init import g_facebook


def dims_connect(terminal: Terminal, server: Server, messenger: ClientMessenger) -> Terminal:
    messenger.delegate = server
    messenger.terminal = terminal
    server.messenger = messenger
    server.server_delegate = terminal
    # client
    terminal.messenger = messenger
    terminal.start(server=server)
    # server.handshake()
    return terminal


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
Log.info('-------- Current station: %s (%s:%d)' % (station_id, local_host, local_port))
g_station = Server(identifier=station_id, host=local_host, port=local_port)
g_facebook.cache_user(user=g_station)

Log.info('======== configuration OK!')
