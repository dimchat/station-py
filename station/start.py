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
    DIM Station
    ~~~~~~~~~~~

    DIM network server node
"""

from socketserver import TCPServer, ThreadingTCPServer

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.utils import Log
from libs.utils.mtp import Server as UDPServer

from station.handler import RequestHandler
from station.config import g_receptionist, g_dispatcher, current_station


if __name__ == '__main__':

    current_station.running = True
    g_receptionist.start()
    g_dispatcher.start()

    # start UDP Server
    Log.info('>>> UDP server (%s:%d) starting ...' % (current_station.host, current_station.port))
    g_udp_server = UDPServer(host=current_station.host, port=current_station.port)
    g_udp_server.start()

    # start TCP Server
    try:
        TCPServer.allow_reuse_address = True
        server = ThreadingTCPServer(server_address=(current_station.host, current_station.port),
                                    RequestHandlerClass=RequestHandler)
        Log.info('server (%s:%s) is listening...' % (current_station.host, current_station.port))
        server.serve_forever()
    except KeyboardInterrupt as ex:
        Log.info('~~~~~~~~ %s' % ex)
    finally:
        current_station.running = False
        Log.info('======== station shutdown!')
