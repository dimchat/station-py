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

from typing import List

from dimp import ID

from dimsdk.ans import keywords as ans_keywords
from dimsdk import Station

#
#  Common Libs
#
from libs.utils import Log
from libs.common import AddressNameServer
from libs.common import Storage, Database
from libs.server import ServerFacebook, ServerMessenger
from libs.server import Dispatcher
from libs.server import ApplePushNotificationService

#
#  Configurations
#
from etc.cfg_apns import apns_credentials, apns_use_sandbox, apns_topic
from etc.cfg_db import base_dir, ans_reserved_records
from etc.cfg_admins import administrators
from etc.cfg_gsp import all_stations, local_servers
from etc.cfg_gsp import station_id, station_host, station_port, station_name
from etc.cfg_bots import group_assistants

from etc.cfg_loader import load_station

from .receptionist import Receptionist
from .monitor import Monitor


Log.info("local storage directory: %s" % base_dir)
Storage.root = base_dir

g_database = Database()


"""
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    A map for short name to ID, just like DNS
"""
g_ans = AddressNameServer()

"""
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""
g_facebook = ServerFacebook()


"""
    Apple Push Notification service (APNs)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A service for pushing notification to offline device
"""
g_apns = ApplePushNotificationService(apns_credentials, use_sandbox=apns_use_sandbox)
g_apns.topic = apns_topic
g_apns.delegate = g_database
Log.info('APNs credentials: %s' % apns_credentials)


"""
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""
g_dispatcher = Dispatcher()
g_dispatcher.apns = g_apns


"""
    DIM Network Monitor
    ~~~~~~~~~~~~~~~~~~~

    A dispatcher for sending reports to administrator(s)
"""
g_monitor = Monitor()
g_monitor.apns = g_apns


"""
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""
g_receptionist = Receptionist()
g_receptionist.apns = g_apns


"""
    Messenger for Local Station
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ServerMessenger()


"""
    Station Info Loaders
    ~~~~~~~~~~~~~~~~~~~~
    
    Loading station info from service provider configuration
"""


def neighbor_stations(identifier: ID) -> List[Station]:
    """ Get neighbor stations for broadcast """
    count = len(all_stations)
    if count <= 1:
        # only 1 station, no neighbors
        return []
    # current station's position
    pos = 0
    for station in all_stations:
        if station.identifier == identifier:
            # got it
            break
        pos = pos + 1
    assert pos < count, 'current station not found: %s, %s' % (identifier, all_stations)
    array = []
    # get left node
    left = all_stations[pos - 1]
    assert left.identifier != identifier, 'stations error: %s' % all_stations
    array.append(left)
    if count > 2:
        # get right node
        right = all_stations[(pos + 1) % count]
        assert right.identifier != identifier, 'stations error: %s' % all_stations
        assert right.identifier != left.identifier, 'stations error: %s' % all_stations
        array.append(right)
    return array


def create_server(identifier: str, host: str, port: int=9394) -> Station:
    """ Create Local Server """
    identifier = ID.parse(identifier=identifier)
    server = Station(identifier=identifier, host=host, port=port)
    g_facebook.cache_user(user=server)
    Log.info('local station created: %s' % server)
    return server


"""
    Loading info
    ~~~~~~~~~~~~
"""

# load ANS reserved records
Log.info('-------- Loading ANS reserved records')
for key, value in ans_reserved_records.items():
    _id = ID.parse(identifier=value)
    assert _id is not None, 'ANS record error: %s, %s' % (key, value)
    Log.info('Name: %s -> ID: %s' % (key, _id))
    if key in ans_keywords:
        # remove reserved name temporary
        index = ans_keywords.index(key)
        ans_keywords.remove(key)
        g_ans.save(key, _id)
        ans_keywords.insert(index, key)
    else:
        # not reserved name, save it directly
        g_ans.save(key, _id)


# scan accounts
Log.info('-------- scanning accounts')
g_database.scan_ids()

# convert string to IDs
Log.info('-------- Loading group assistants: %d' % len(group_assistants))
group_assistants = [ID.parse(identifier=item) for item in group_assistants]
Log.info('Group assistants: %s' % group_assistants)
g_facebook.group_assistants = group_assistants

# convert ID to Station
Log.info('-------- Loading stations: %d' % len(all_stations))
all_stations = [load_station(identifier=item, facebook=g_facebook) for item in all_stations]

# convert ID to Server
Log.info('-------- creating servers: %d' % len(local_servers))
local_servers = [create_server(identifier=item, host=station_host, port=station_port) for item in local_servers]

# current station
current_station = None
station_id = ID.parse(identifier=station_id)
for srv in local_servers:
    if srv.identifier == station_id:
        # got it
        current_station = srv
        break
assert current_station is not None, 'current station not created: %s' % station_id
Log.info('current station(%s): %s' % (station_name, current_station))

# set local users for facebook
g_facebook.local_users = local_servers
g_facebook.current_user = current_station
# set current station for key store
g_messenger.key_store.user = current_station
# set current station for dispatcher
g_dispatcher.station = current_station
# set current station for receptionist
g_receptionist.station = current_station
# set current station as the report sender
g_monitor.sender = current_station.identifier

# load neighbour station for delivering message
neighbors = neighbor_stations(identifier=current_station.identifier)
Log.info('-------- Loading neighbor stations: %d' % len(neighbors))
for node in neighbors:
    Log.info('add node: %s' % node)
    g_dispatcher.add_neighbor(station=node)

# load admins for receiving system reports
Log.info('-------- Loading administrators: %d' % len(administrators))
administrators = [ID.parse(identifier=item) for item in administrators]
for admin in administrators:
    Log.info('add admin: %s' % admin)
    g_monitor.admins.add(admin)

Log.info('======== configuration OK!')
