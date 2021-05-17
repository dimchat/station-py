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
    DIM Station Config
    ~~~~~~~~~~~~~~~~~~

    Configuration for DIM network server node
"""

#
#  Common Libs
#
from libs.utils import Log
from libs.push import ApplePushNotificationService
from libs.server import ServerMessenger
from libs.server import Dispatcher

#
#  Configurations
#
from etc.config import apns_credentials, apns_use_sandbox, apns_topic
from etc.config import bind_host, bind_port

from etc.cfg_init import g_database, g_facebook, g_keystore
from etc.cfg_init import station_id, create_station, neighbor_stations


"""
    Messenger
    ~~~~~~~~~

    Transceiver for processing messages
"""
g_messenger = ServerMessenger()
g_facebook.messenger = g_messenger


"""
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""
g_dispatcher = Dispatcher()


"""
    Push Notification Service
    ~~~~~~~~~~~~~~~~~~~~~~~~~
"""
if apns_credentials is not None:
    g_push_service = ApplePushNotificationService(credentials=apns_credentials,
                                                  use_sandbox=apns_use_sandbox)
    g_push_service.topic = apns_topic
    g_push_service.delegate = g_database
    g_dispatcher.push_service = g_push_service


"""
    Local Station
    ~~~~~~~~~~~~~
"""
Log.info('-------- Creating local server: %s (%s:%d)' % (station_id, bind_host, bind_port))
g_station = create_station(info={
    'ID': station_id,
    'host': bind_host,
    'port': bind_port
})
assert g_station is not None, 'current station not created: %s' % station_id
Log.info('Current station: %s' % g_station)

# set local users for facebook
g_facebook.local_users = [g_station]
g_facebook.current_user = g_station
# set current station for key store
g_keystore.user = g_station
# set current station for dispatcher
g_dispatcher.station = g_station.identifier

# load neighbour station for delivering message
Log.info('-------- Loading neighbor stations: %d' % len(neighbor_stations))
for node in neighbor_stations:
    assert node != g_station, 'neighbor station error: %s, %s' % (node, g_station)
    Log.info('add node: %s' % node)
    g_dispatcher.add_neighbor(station=node.identifier)

Log.info('======== configuration OK! ========')
