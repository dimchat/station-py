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
from libs.push import NotificationPusher

from etc.cfg_init import g_cleaner

from station.handler import RequestHandler
from station.config import g_station, g_dispatcher
from station.monitor import Monitor
from station.receptionist import Receptionist


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
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
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
    DIM Network Monitor
    ~~~~~~~~~~~~~~~~~~~

    A dispatcher for sending reports to administrator(s)
"""
g_monitor = Monitor()


"""
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""
g_receptionist = Receptionist()
# set current station for receptionist
g_receptionist.station = g_station.identifier


"""
    Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_pns = NotificationPusher()


if __name__ == '__main__':

    g_monitor.start()
    g_receptionist.start()
    g_dispatcher.start()
    g_pns.start()

    # start UDP Server
    Log.info('>>> UDP server (%s:%d) starting ...' % (g_station.host, g_station.port))
    g_udp_server = UDPServer(host=g_station.host, port=g_station.port)
    g_udp_server.start()

    # start TCP Server
    try:
        # # ThreadingTCPServer.allow_reuse_address = True
        # server = ThreadingTCPServer(server_address=(g_station.host, g_station.port),
        #                             RequestHandlerClass=RequestHandler,
        #                             bind_and_activate=False)
        # Log.info('>>> TCP server (%s:%d) starting...' % (g_station.host, g_station.port))
        # server.allow_reuse_address = True
        # server.server_bind()
        # server.server_activate()
        # Log.info('>>> TCP server (%s:%d) is listening...' % (g_station.host, g_station.port))
        # server.serve_forever()
        server = TCPServer(server_address=(g_station.host, g_station.port),
                           request_handler_class=RequestHandler)
        Log.info('>>> TCP server (%s:%d) starting...' % (g_station.host, g_station.port))
        spawn(server.start).join()
    except KeyboardInterrupt as ex:
        Log.info('~~~~~~~~ %s' % ex)
    finally:
        g_cleaner.stop()
        g_udp_server.stop()
        g_pns.stop()
        g_dispatcher.stop()
        g_receptionist.stop()
        g_monitor.stop()
        Log.info('======== station shutdown!')
