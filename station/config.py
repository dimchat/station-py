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

from dimp import PrivateKey, Meta, Profile
from dimsdk import AddressNameService
from dimsdk import Station, KeyStore

from dimsdk import ApplePushNotificationService
from dimsdk import ChatBot, Tuling, XiaoI

#
#  Common Libs
#
from libs.common import Log
from libs.common import Database, Facebook
from libs.server import SessionServer, Server

from libs.common.immortals import moki_id, moki_sk, moki_meta, moki_profile
from libs.common.immortals import hulk_id, hulk_sk, hulk_meta, hulk_profile

#
#  Configurations
#
from etc.cfg_apns import apns_credentials, apns_use_sandbox, apns_topic
from etc.cfg_db import base_dir
from etc.cfg_admins import administrators
from etc.cfg_gsp import all_stations, local_servers, load_station_info
from etc.cfg_gsp import station_id, station_host, station_port, station_name
from etc.cfg_bots import tuling_keys, tuling_ignores, xiaoi_keys, xiaoi_ignores

from .dispatcher import Dispatcher
from .receptionist import Receptionist
from .monitor import Monitor


"""
    Key Store
    ~~~~~~~~~

    Memory cache for reused passwords (symmetric key)
"""
g_keystore = KeyStore()


"""
    Database
    ~~~~~~~~

    for cached messages, profile manage(Barrack), reused symmetric keys(KeyStore)
"""
g_database = Database()
g_database.base_dir = base_dir
Log.info("database directory: %s" % g_database.base_dir)


"""
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    A map for short name to ID, just like DNS
"""
g_ans = AddressNameService()
g_ans.database = g_database


"""
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""
g_facebook = Facebook()
g_facebook.database = g_database
g_facebook.ans = g_ans


"""
    Session Server
    ~~~~~~~~~~~~~~

    for login user
"""
g_session_server = SessionServer()


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
g_dispatcher.database = g_database
g_dispatcher.facebook = g_facebook
g_dispatcher.session_server = g_session_server
g_dispatcher.apns = g_apns


"""
    DIM Network Monitor
    ~~~~~~~~~~~~~~~~~~~

    A dispatcher for sending reports to administrator(s)
"""
g_monitor = Monitor()
g_monitor.database = g_database
g_monitor.facebook = g_facebook
g_monitor.keystore = g_keystore
g_monitor.session_server = g_session_server
g_monitor.apns = g_apns


"""
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""
g_receptionist = Receptionist()
g_receptionist.session_server = g_session_server
g_receptionist.database = g_database
g_receptionist.apns = g_apns


"""
    Chat Bots
    ~~~~~~~~~

    Chat bots from 3rd-party
"""


def chat_bot(name: str) -> ChatBot:
    if 'tuling' == name:
        # Tuling
        key = tuling_keys.get('api_key')
        tuling = Tuling(api_key=key)
        # ignore codes
        for item in tuling_ignores:
            if item not in tuling.ignores:
                tuling.ignores.append(item)
        return tuling
    elif 'xiaoi' == name:
        # XiaoI
        key = xiaoi_keys.get('app_key')
        secret = xiaoi_keys.get('app_secret')
        xiaoi = XiaoI(app_key=key, app_secret=secret)
        # ignore responses
        for item in xiaoi_ignores:
            if item not in xiaoi.ignores:
                xiaoi.ignores.append(item)
        return xiaoi
    else:
        raise NotImplementedError('unknown chat bot: %s' % name)


"""
    Station Info Loaders
    ~~~~~~~~~~~~~~~~~~~~
    
    Loading station info from service provider configuration
"""


def neighbor_stations(identifier: str) -> list:
    """ Get neighbor stations for broadcast """
    identifier = g_facebook.identifier(identifier)
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


def load_station(identifier: str) -> Station:
    """ Load station info from 'etc' directory

        :param identifier - station ID
        :return station with info from 'dims/etc/{address}/*'
    """
    identifier = g_facebook.identifier(identifier)
    # check meta
    meta = g_facebook.meta(identifier=identifier)
    if meta is None:
        # load from 'etc' directory
        meta = Meta(load_station_info(identifier=identifier, filename='meta.js'))
        if meta is None:
            raise LookupError('failed to get meta for station: %s' % identifier)
        elif not g_facebook.save_meta(meta=meta, identifier=identifier):
            raise ValueError('meta error: %s' % meta)
    # check private key
    private_key = g_facebook.private_key_for_signature(identifier=identifier)
    if private_key is None:
        # load from 'etc' directory
        private_key = PrivateKey(load_station_info(identifier=identifier, filename='secret.js'))
        if private_key is None:
            pass
        elif not g_facebook.save_private_key(private_key=private_key, identifier=identifier):
            raise AssertionError('failed to save private key for ID: %s, %s' % (identifier, private_key))
    # check profile
    profile = load_station_info(identifier=identifier, filename='profile.js')
    if profile is None:
        raise LookupError('failed to get profile for station: %s' % identifier)
    Log.info('station profile: %s' % profile)
    name = profile.get('name')
    host = profile.get('host')
    port = profile.get('port')
    # create station
    if private_key is None:
        # remote station
        station = Station(identifier=identifier, host=host, port=port)
    else:
        # create profile
        profile = Profile.new(identifier=identifier)
        profile.set_property('name', name)
        profile.set_property('host', host)
        profile.set_property('port', port)
        profile.sign(private_key=private_key)
        if not g_facebook.save_profile(profile=profile):
            raise AssertionError('failed to save profile: %s' % profile)
        # local station
        station = Server(identifier=identifier, host=host, port=port)
    g_facebook.cache_user(user=station)
    Log.info('station loaded: %s' % station)
    return station


def create_server(identifier: str, host: str, port: int=9394) -> Server:
    """ Create Local Server """
    identifier = g_facebook.identifier(identifier)
    server = Server(identifier=identifier, host=host, port=port)
    g_facebook.cache_user(user=server)
    Log.info('local station created: %s' % server)
    return server


def load_immortals():
    # load immortals
    Log.info('immortal user: %s' % moki_id)
    g_facebook.save_meta(identifier=moki_id, meta=moki_meta)
    g_facebook.save_private_key(identifier=moki_id, private_key=moki_sk)
    g_facebook.save_profile(profile=moki_profile)

    Log.info('immortal user: %s' % hulk_id)
    g_facebook.save_meta(identifier=hulk_id, meta=hulk_meta)
    g_facebook.save_private_key(identifier=hulk_id, private_key=hulk_sk)
    g_facebook.save_profile(profile=hulk_profile)


"""
    Loading info
    ~~~~~~~~~~~~
"""

# load immortal accounts
Log.info('-------- loading immortals accounts')
load_immortals()

# scan accounts
Log.info('-------- scanning accounts')
g_database.scan_ids()

# convert ID to Station
Log.info('-------- loading stations: %d' % len(all_stations))
all_stations = [load_station(identifier=item) for item in all_stations]

# convert string to ID
Log.info('-------- loading administrators: %d' % len(administrators))
administrators = [g_facebook.identifier(item) for item in administrators]

# convert ID to Server
Log.info('-------- creating servers: %d' % len(local_servers))
local_servers = [create_server(identifier=item, host=station_host, port=station_port) for item in local_servers]

# current station
current_station = None
station_id = g_facebook.identifier(station_id)
for srv in local_servers:
    if srv.identifier == station_id:
        # got it
        current_station = srv
        break
assert current_station is not None, 'current station not created: %s' % station_id
Log.info('current station(%s): %s' % (station_name, current_station))

# set current station for key store
g_keystore.user = current_station
# set current station for receptionist
g_receptionist.station = current_station
# set current station as the report sender
g_monitor.sender = current_station.identifier

# load neighbour station for delivering message
neighbors = neighbor_stations(identifier=current_station.identifier)
Log.info('-------- loading neighbor stations: %d' % len(neighbors))
for node in neighbors:
    Log.info('add node: %s' % node)
    g_dispatcher.neighbors.append(node)

# load admins for receiving system reports
Log.info('-------- loading administrators: %d' % len(administrators))
administrators = [g_facebook.identifier(item) for item in administrators]
for admin in administrators:
    Log.info('add admin: %s' % admin)
    g_monitor.admins.add(admin)

Log.info('======== configuration OK!')
