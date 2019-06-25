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

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from dimp import ID

from common import keystore, database, load_accounts
from common import s001, s001_host, s001_port

from station.handler import RequestHandler
from station.receptionist import receptionist
from station.monitor import monitor
from station.apns import apns
from station.gsp_admins import administrators


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
station = s001
station_host = s001_host
station_port = s001_port

"""
    Database
    ~~~~~~~~

    for cached messages, profile manage(Barrack), reused symmetric keys(KeyStore)
"""
# database.base_dir = '/data/.dim/'

"""
    Apple Push Notification service (APNs)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A service for pushing notification to offline device
"""
apns.credentials = '/data/.dim/private/apns-key.pem'

"""
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""
receptionist.station = station

"""
    DIM Network Monitor
    ~~~~~~~~~~~~~~~~~~~

    A dispatcher for sending reports to administrator(s)
"""
# set station as the report sender, and add admins who will receive reports
monitor.sender = station.identifier
for admin in administrators:
    monitor.admins.add(ID(admin))


if __name__ == '__main__':
    load_accounts(database=database)

    keystore.user = station

    station.running = True
    receptionist.start()

    # start TCP Server
    try:
        TCPServer.allow_reuse_address = True
        server = ThreadingTCPServer(server_address=(station_host, station_port),
                                    RequestHandlerClass=RequestHandler)
        print('server (%s:%s) is listening...' % (station_host, station_port))
        server.serve_forever()
    except KeyboardInterrupt as ex:
        print('~~~~~~~~', ex)
    finally:
        station.running = False
        print('======== station shutdown!')
