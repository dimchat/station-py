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

from socketserver import ThreadingTCPServer

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Log
from libs.utils.mtp import Server as UDPServer
from libs.push import PushCenter
from libs.server import Dispatcher
from libs.server import ReceptionistCaller, SearchEngineCaller
from libs.server import OctopusCaller, MonitorCaller

from etc.cfg_init import neighbor_stations

from station.config import g_station
from station.handler import RequestHandler


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


"""
    DIM Search Engine
    ~~~~~~~~~~~~~~~~~

    An engine support 'search' command
"""
g_search_engine = SearchEngineCaller()


"""
    DIM Network Monitor
    ~~~~~~~~~~~~~~~~~~~

    A dispatcher for sending reports to administrator(s)
"""
g_monitor = MonitorCaller()


"""
    Station Bridge
    ~~~~~~~~~~~~~~
"""
g_octopus = OctopusCaller()
g_octopus.station = g_station


"""
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""
g_receptionist = ReceptionistCaller()


if __name__ == '__main__':

    g_dispatcher.start()

    # start UDP Server
    Log.info('>>> UDP server (%s:%d) starting ...' % (g_station.host, g_station.port))
    g_udp_server = UDPServer(host=g_station.host, port=g_station.port)
    g_udp_server.start()

    # start TCP Server
    try:
        # ThreadingTCPServer.allow_reuse_address = True
        server = ThreadingTCPServer(server_address=(g_station.host, g_station.port),
                                    RequestHandlerClass=RequestHandler,
                                    bind_and_activate=False)
        Log.info('>>> TCP server (%s:%d) starting...' % (g_station.host, g_station.port))
        server.allow_reuse_address = True
        server.server_bind()
        server.server_activate()
        Log.info('>>> TCP server (%s:%d) is listening...' % (g_station.host, g_station.port))
        server.serve_forever()
    except KeyboardInterrupt as ex:
        Log.info('~~~~~~~~ %s' % ex)
    finally:
        g_udp_server.stop()
        g_dispatcher.stop()
        Log.info('======== station shutdown!')
