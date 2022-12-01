#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

import socket
import traceback
from typing import Optional

from gevent import spawn, monkey

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

monkey.patch_all()

from libs.utils import Log, Logging
from libs.utils.mtp import Server as UDPServer
from libs.push import PushCenter
from libs.server import Dispatcher

from etc.cfg_init import neighbor_stations

from station.config import g_station
from station.handler import RequestHandler


class TCPServer(Logging):

    def __init__(self, server_address: tuple, request_handler_class):
        super().__init__()
        self.__address = server_address
        self.__request_handler_class = request_handler_class
        self.__sock: Optional[socket.socket] = None

    def start(self):
        sock = self.__sock
        if sock is not None:
            sock.close()
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(self.__address)
        sock.listen(8)
        self.__sock = sock
        self.run()

    def run(self):
        while True:
            sock, address = self.__sock.accept()
            spawn(self._handle_request, sock, address)

    def _handle_request(self, sock: socket.socket, address: tuple):
        try:
            self.__request_handler_class(request=sock, client_address=address, server=self)
        except Exception as error:
            self.error(msg='handle request error: %s' % error)
            traceback.print_exc()


"""
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""
g_dispatcher = Dispatcher()
g_dispatcher.push_service = PushCenter()
# set current station for dispatcher
g_dispatcher.station = g_station.identifier

# load neighbour station for delivering message
Log.info('-------- Loading neighbor stations: %d' % len(neighbor_stations))
for node in neighbor_stations:
    assert node != g_station, 'neighbor station error: %s, %s' % (node, g_station)
    Log.info('add node: %s' % node)
    g_dispatcher.add_neighbor(station=node.identifier)


if __name__ == '__main__':

    g_dispatcher.start()

    # start UDP Server
    Log.info('>>> UDP server (%s:%d) starting ...' % (g_station.host, g_station.port))
    g_udp_server = UDPServer(host=g_station.host, port=g_station.port)
    g_udp_server.start()

    # start TCP Server
    try:
        server = TCPServer(server_address=(g_station.host, g_station.port),
                           request_handler_class=RequestHandler)
        Log.info('>>> TCP server (%s:%d) starting...' % (g_station.host, g_station.port))
        spawn(server.start).join()
    except KeyboardInterrupt as ex:
        Log.info('~~~~~~~~ %s' % ex)
    finally:
        g_udp_server.stop()
        g_dispatcher.stop()
        Log.info('======== station shutdown!')
