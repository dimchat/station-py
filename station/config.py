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

import os

from mkm import Meta, PrivateKey

from dimp import Profile, Station

from common import Log, Storage, Server
from common import Database, Facebook, KeyStore, Messenger
from common import ApplePushNotificationService, SessionServer

from common.immortals import moki_id, moki_sk, moki_meta, moki_profile
from common.immortals import hulk_id, hulk_sk, hulk_meta, hulk_profile

from .cfg_db import base_dir, apns_credentials
from .cfg_admins import administrators
from .cfg_gsp import all_stations, local_servers
from .cfg_gsp import station_id, station_host, station_port

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
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""
g_facebook = Facebook()
g_facebook.database = g_database


"""
    Messenger
    ~~~~~~~~~
"""
g_messenger = Messenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore


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
g_apns = ApplePushNotificationService(apns_credentials, use_sandbox=True)
g_apns.delegate = g_database


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
g_monitor.messenger = g_messenger
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
    # get root path
    path = os.path.abspath(os.path.dirname(__file__))
    root = os.path.split(path)[0]
    directory = os.path.join(root, 'etc', identifier.address)
    # check profile
    profile = Storage.read_json(path=os.path.join(directory, 'profile.js'))
    if profile is None:
        raise LookupError('failed to get profile for station: %s' % identifier)
    # station name
    name = profile.get('name')
    host = profile.get('host')
    port = profile.get('port')
    Log.info('loading station %s (%s:%d)...' % (name, host, port))
    # check meta
    meta = g_facebook.meta(identifier=identifier)
    if meta is None:
        # load from 'etc' directory
        meta = Meta(Storage.read_json(path=os.path.join(directory, 'meta.js')))
        if meta is None:
            raise LookupError('failed to get meta for station: %s' % identifier)
        elif not g_facebook.save_meta(meta=meta, identifier=identifier):
            raise ValueError('meta error: %s' % meta)
    # check private key
    private_key = g_facebook.private_key_for_signature(identifier=identifier)
    if private_key is None:
        # load from 'etc' directory
        private_key = PrivateKey(Storage.read_json(path=os.path.join(directory, 'secret.js')))
        if private_key is None:
            pass
        elif not g_facebook.save_private_key(private_key=private_key, identifier=identifier):
            raise AssertionError('failed to save private key for ID: %s, %s' % (identifier, private_key))
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
    return station


def create_server(identifier: str, host: str, port: int=9394) -> Server:
    """ Create Local Server """
    identifier = g_facebook.identifier(identifier)
    server = Server(identifier=identifier, host=host, port=port)
    server.delegate = g_facebook
    server.messenger = g_messenger
    return server


def load_accounts(facebook, database):
    """ Prepare accounts """
    Log.info('======== loading accounts')

    # load immortals
    Log.info('loading immortal user: %s' % moki_id)
    facebook.save_meta(identifier=moki_id, meta=moki_meta)
    facebook.save_private_key(identifier=moki_id, private_key=moki_sk)
    facebook.save_profile(profile=moki_profile)

    Log.info('loading immortal user: %s' % hulk_id)
    facebook.save_meta(identifier=hulk_id, meta=hulk_meta)
    facebook.save_private_key(identifier=hulk_id, private_key=hulk_sk)
    facebook.save_profile(profile=hulk_profile)

    # scan accounts
    database.scan_ids()
    Log.info('======== loaded')


"""
    Loading info
    ~~~~~~~~~~~~
"""

# convert ID to admin
Log.info('loading administrators: %s' % administrators)
administrators = [g_facebook.identifier(item) for item in administrators]
# add admins who will receive reports
for admin in administrators:
    g_monitor.admins.add(admin)

# convert ID to Station
Log.info('loading stations: %s' % all_stations)
all_stations = [load_station(identifier=item) for item in all_stations]

# convert ID to Server
Log.info('creating servers: %s' % local_servers)
local_servers = [create_server(identifier=item, host=station_host, port=station_port) for item in local_servers]

# current station
station_id = g_facebook.identifier(station_id)
# create station
current_station = Server(identifier=station_id, host=station_host, port=station_port)
current_station.delegate = g_facebook
current_station.messenger = g_messenger
Log.info('current station: %s' % current_station)

# set current station for key store
g_keystore.user = current_station
# set current station for receptionist
g_receptionist.station = current_station
# set current station as the report sender
g_monitor.sender = current_station.identifier
