#! /usr/bin/env python
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
from threading import Thread
from time import sleep

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from station.config import database, session_server, station
from station.config import load_accounts
from station.handler import DIMRequestHandler


def session_scanner(ss, db):
    while True:
        # scan sessions
        sessions = ss.sessions.copy()
        for identifier in sessions:
            request = sessions[identifier].request
            if request:
                # if session connected, scan messages for it
                messages = db.load_messages(identifier=identifier)
                for msg in messages:
                    request.send(msg)
        # sleep 1 second for next loop
        sleep(1.0)


if __name__ == '__main__':
    load_accounts()

    # start transponder
    scanner = Thread(target=session_scanner, args=(session_server, database))
    print('starting scanner')
    scanner.start()

    # start TCP server
    TCPServer.allow_reuse_address = True
    server_address = (station.host, station.port)
    server = ThreadingTCPServer(server_address=server_address,
                                RequestHandlerClass=DIMRequestHandler)
    print('server (%s:%s) is listening...' % server_address)
    server.serve_forever()
