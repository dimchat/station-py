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

from dimples.utils import Log
from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils.mtp import Server as UDPServer

from station.shared import prepare_server
from station.handler import RequestHandler


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/station.ini'


def main():
    shared = prepare_server(server_name='DIM Network Station', default_config=DEFAULT_CONFIG)
    config = shared.config
    # check bind host & port
    host = config.station_host
    port = config.station_port
    assert host is not None and port > 0, 'station config error: %s' % config
    server_address = (host, port)

    # start UDP Server
    Log.info('>>> UDP server %s starting ...' % str(server_address))
    g_udp_server = UDPServer(host=server_address[0], port=server_address[1])
    g_udp_server.start()

    # start TCP server
    try:
        # ThreadingTCPServer.allow_reuse_address = True
        server = ThreadingTCPServer(server_address=server_address,
                                    RequestHandlerClass=RequestHandler,
                                    bind_and_activate=False)
        Log.info(msg='>>> TCP server %s starting...' % str(server_address))
        server.allow_reuse_address = True
        server.server_bind()
        server.server_activate()
        server.serve_forever()
    except KeyboardInterrupt as ex:
        Log.info(msg='~~~~~~~~ %s' % ex)
    finally:
        g_udp_server.stop()
        Log.info(msg='======== station shutdown!')


if __name__ == '__main__':
    main()
