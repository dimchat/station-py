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
    Robot Config
    ~~~~~~~~~~~~

    Configuration for Robot
"""

from typing import Optional

from dimp import PrivateKey, Meta, ID, Profile, User
from dimsdk import Station, KeyStore
from dimsdk import ChatBot, Tuling, XiaoI
from dimsdk.ans import keywords as ans_keywords

#
#  Common Libs
#
from libs.common import Log
from libs.common import Database, AddressNameServer
from libs.client import Terminal, ClientMessenger, ClientFacebook

#
#  Configurations
#
from etc.cfg_db import base_dir, ans_reserved_records
from etc.cfg_gsp import station_id, all_stations
from etc.cfg_bots import group_naruto
from etc.cfg_bots import tuling_keys, tuling_ignores, xiaoi_keys, xiaoi_ignores
from etc.cfg_bots import lingling_id, xiaoxiao_id, assistant_id, chatroom_id

from etc.cfg_loader import load_robot_info, load_station

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
g_ans = AddressNameServer()
g_ans.database = g_database


"""
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""
g_facebook = ClientFacebook()
g_facebook.database = g_database
g_facebook.ans = g_ans


"""
    Messenger for client
    ~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore
g_facebook.messenger = g_messenger


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
station_id = g_facebook.identifier(station_id)

station_host = '127.0.0.1'
# station_host = '134.175.87.98'  # dimchat-gz
# station_host = '124.156.108.150'  # dimchat-hk
station_port = 9394

g_station = Station(identifier=station_id, host=station_host, port=station_port)
g_facebook.cache_user(user=g_station)
g_messenger.set_context('station', g_station)

# Address Name Service
g_ans.save('station', g_station.identifier)
g_ans.save('moki', g_facebook.identifier('moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk'))
g_ans.save('hulk', g_facebook.identifier('hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj'))


"""
    Chat Bots
    ~~~~~~~~~

    Chat bots from 3rd-party
"""


def chat_bot(name: str) -> Optional[ChatBot]:
    if 'tuling' == name:
        if tuling_keys is None or tuling_ignores is None:
            return None
        # Tuling
        api_key = tuling_keys.get('api_key')
        assert api_key is not None, 'Tuling keys error: %s' % tuling_keys
        tuling = Tuling(api_key=api_key)
        # ignore codes
        for item in tuling_ignores:
            if item not in tuling.ignores:
                tuling.ignores.append(item)
        return tuling
    elif 'xiaoi' == name:
        if xiaoi_keys is None or xiaoi_ignores is None:
            return None
        # XiaoI
        app_key = xiaoi_keys.get('app_key')
        app_secret = xiaoi_keys.get('app_secret')
        assert app_key is not None and app_secret is not None, 'XiaoI keys error: %s' % xiaoi_keys
        xiaoi = XiaoI(app_key=app_key, app_secret=app_secret)
        # ignore responses
        for item in xiaoi_ignores:
            if item not in xiaoi.ignores:
                xiaoi.ignores.append(item)
        return xiaoi
    else:
        raise NotImplementedError('unknown chat bot: %s' % name)


"""
    Client
    ~~~~~~
    
"""


def load_user(identifier: str) -> User:
    identifier = g_facebook.identifier(identifier)
    # check meta
    try:
        meta = g_facebook.meta(identifier=identifier)
    except AssertionError:
        meta = None
    if meta is None:
        # load from 'etc' directory
        meta = Meta(load_robot_info(identifier=identifier, filename='meta.js'))
        if meta is None:
            raise LookupError('failed to get meta for robot: %s' % identifier)
        elif not g_facebook.save_meta(meta=meta, identifier=identifier):
            raise ValueError('meta error: %s' % meta)
    # check private key
    private_key = g_facebook.private_key_for_signature(identifier=identifier)
    if private_key is None:
        # load from 'etc' directory
        private_key = PrivateKey(load_robot_info(identifier=identifier, filename='secret.js'))
        if private_key is None:
            pass
        elif not g_facebook.save_private_key(key=private_key, identifier=identifier):
            raise AssertionError('failed to save private key for ID: %s, %s' % (identifier, private_key))
    if private_key is None:
        raise AssertionError('private key not found for ID: %s' % identifier)
    # check profile
    profile = load_robot_info(identifier=identifier, filename='profile.js')
    if profile is None:
        raise LookupError('failed to get profile for robot: %s' % identifier)
    Log.info('robot profile: %s' % profile)
    name = profile.get('name')
    avatar = profile.get('avatar')
    # create profile
    profile = Profile.new(identifier=identifier)
    profile.set_property('name', name)
    profile.set_property('avatar', avatar)
    profile.sign(private_key=private_key)
    if not g_facebook.save_profile(profile):
        raise AssertionError('failed to save profile: %s' % profile)
    # create local user
    return g_facebook.user(identifier=identifier)


def create_client(user: User) -> Terminal:
    g_facebook.current_user = user
    client = Terminal()
    client.messenger = g_messenger
    # context
    client.messenger.context['database'] = g_database
    client.messenger.context['remote_address'] = (g_station.host, g_station.port)
    client.messenger.context['handshake_delegate'] = client
    # connect
    client.connect(station=g_station)
    client.handshake()
    return client


"""
    Shodai Hokage
    ~~~~~~~~~~~~~
    
    A group contains all freshmen
"""


def load_naruto():
    gid = g_facebook.identifier(group_naruto)
    Log.info('naruto group: %s' % gid)
    meta = Meta(load_robot_info(gid, 'meta.js'))
    g_facebook.save_meta(identifier=gid, meta=meta)


def load_freshmen() -> list:
    freshmen = []
    from etc.cfg_bots import load_freshmen as _loader
    array = _loader()
    if array is not None:
        for item in array:
            identifier = g_facebook.identifier(item)
            if identifier is None:
                Log.error('ID error: %s' % item)
            elif identifier.is_user:
                freshmen.append(identifier)
            else:
                # Log.error('Not a user ID: %s' % identifier)
                pass
    return freshmen


"""
    Loading info
    ~~~~~~~~~~~~
"""

# load ANS reserved records
Log.info('-------- loading ANS reserved records')
for key, value in ans_reserved_records.items():
    value = ID(value)
    assert value.valid, 'ANS record error: %s, %s' % (key, value)
    Log.info('Name: %s -> ID: %s' % (key, value))
    if key in ans_keywords:
        # remove reserved name temporary
        index = ans_keywords.index(key)
        ans_keywords.remove(key)
        g_ans.save(key, value)
        ans_keywords.insert(index, key)
    else:
        # not reserved name, save it directly
        g_ans.save(key, value)

# convert ID to Station
Log.info('-------- loading stations: %d' % len(all_stations))
all_stations = [load_station(identifier=item, facebook=g_facebook) for item in all_stations]

# load group 'DIM Plaza'
Log.info('-------- loading group contains all users')
load_naruto()

lingling_id = g_facebook.identifier(string=lingling_id)
xiaoxiao_id = g_facebook.identifier(string=xiaoxiao_id)
assistant_id = g_facebook.identifier(string=assistant_id)
chatroom_id = g_facebook.identifier(string=chatroom_id)

Log.info('Chat bot: %s' % lingling_id)
Log.info('Chat bot: %s' % xiaoxiao_id)
Log.info('DIM bot: %s' % assistant_id)
Log.info('Chatroom: %s' % chatroom_id)

Log.info('======== configuration OK!')
