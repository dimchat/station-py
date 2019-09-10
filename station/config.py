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

from mkm import Meta, PrivateKey, ID

from dimp import Profile, Station

from common import Log, Storage, Server
from common import Database, Facebook, KeyStore, Messenger
from common import ApplePushNotificationService, SessionServer

from common.immortals import moki_id, moki_sk, moki_meta, moki_profile
from common.immortals import hulk_id, hulk_sk, hulk_meta, hulk_profile

from .cfg_admins import administrators
from .cfg_gsp import stations, station_id, station_name, station_host, station_port

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
g_database.base_dir = '/data/.dim/'
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
"""
g_messenger = Messenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
# create station
current_station = Server(identifier=station_id, host=station_host, port=station_port)
current_station.delegate = g_facebook
current_station.messenger = g_messenger
current_station.running = False

g_keystore.user = current_station


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
apns_credentials = '/data/.dim/private/apns-key.pem'
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

# set station as the report sender, and add admins who will receive reports
g_monitor.sender = current_station.identifier
for admin in administrators:
    g_monitor.admins.add(g_facebook.identifier(admin))


"""
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""
g_receptionist = Receptionist()
g_receptionist.session_server = g_session_server
g_receptionist.database = g_database
g_receptionist.apns = g_apns
g_receptionist.station = current_station


def load_station(identifier: ID) -> Station:
    # get root path
    path = os.path.abspath(os.path.dirname(__file__))
    root = os.path.split(path)[0]
    directory = os.path.join(root, 'etc', identifier.address)
    # check profile
    profile = Storage.read_json(path=os.path.join(directory, 'profile.js'))
    if profile is None:
        raise LookupError('failed to get profile for station: %s' % identifier)
    # station name
    if identifier == current_station.identifier:
        name = station_name
    else:
        name = profile.get('name')
    # station host & port
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
        profile.name = name
        profile.sign(private_key=private_key)
        if not g_facebook.save_profile(profile=profile):
            raise AssertionError('failed to save profile: %s' % profile)
        # local station
        station = Server(identifier=identifier, host=host, port=port)
    g_facebook.cache_user(user=station)
    return station


def load_accounts(facebook, database):
    Log.info('======== loading accounts')

    #
    # load immortals
    #

    Log.info('loading immortal user: %s' % moki_id)
    facebook.save_meta(identifier=moki_id, meta=moki_meta)
    facebook.save_private_key(identifier=moki_id, private_key=moki_sk)
    facebook.save_profile(profile=moki_profile)

    Log.info('loading immortal user: %s' % hulk_id)
    facebook.save_meta(identifier=hulk_id, meta=hulk_meta)
    facebook.save_private_key(identifier=hulk_id, private_key=hulk_sk)
    facebook.save_profile(profile=hulk_profile)

    Log.info('loading stations: %s' % stations)
    for item in stations:
        srv = load_station(identifier=item)
        Log.info('ID: %s, station: %s' % (item, srv))

    #
    # scan accounts
    #

    database.scan_ids()

    Log.info('======== loaded')
