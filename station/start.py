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

import getopt
import sys
from socketserver import ThreadingTCPServer

from dimples.utils import Log
from dimples.utils import Path
from dimples.database import Storage
from dimples import Config

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils.mtp import Server as UDPServer

from station.shared import GlobalVariable
from station.shared import create_database, create_facebook, create_ans
from station.shared import create_pusher, stop_pusher
from station.shared import create_dispatcher, stop_dispatcher
from station.handler import RequestHandler


#
# show logs
#
Log.LEVEL = Log.DEVELOP


DEFAULT_CONFIG = '/etc/dim/station.ini'


def show_help():
    cmd = sys.argv[0]
    print('')
    print('    DIM Network Station')
    print('')
    print('usages:')
    print('    %s [--config=<FILE>]' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('optional arguments:')
    print('    --config        config file path (default: "%s")' % DEFAULT_CONFIG)
    print('    --help, -h      show this help message and exit')
    print('')


def main():
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help()
        sys.exit(1)
    # check options
    ini_file = None
    for opt, arg in opts:
        if opt == '--config':
            ini_file = arg
        else:
            show_help()
            sys.exit(0)
    # check config filepath
    if ini_file is None:
        ini_file = DEFAULT_CONFIG
    if not Storage.exists(path=ini_file):
        show_help()
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load config
    config = Config.load(file=ini_file)
    # initializing
    print('[DB] init with config: %s => %s' % (ini_file, config))
    shared = GlobalVariable()
    shared.config = config
    create_database(shared=shared)
    create_facebook(shared=shared)
    create_ans(shared=shared)
    create_pusher(shared=shared)
    create_dispatcher(shared=shared)

    server_address = (config.station_host, config.station_port)

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
        stop_dispatcher(shared=shared)
        stop_pusher(shared=shared)
        Log.info(msg='======== station shutdown!')


if __name__ == '__main__':
    main()
