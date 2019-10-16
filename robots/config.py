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
from time import sleep

from dimp import ID, PrivateKey, Meta, Profile
from dimp import Station
from dimp import InstantMessage, Content, TextContent

#
#  Common Libs
#
from common import Log
from common import Database, Facebook, AddressNameService, KeyStore, Messenger
from common import Robot, ChatBot, Tuling, XiaoI

from common.immortals import moki_id, moki_sk, moki_meta, moki_profile
from common.immortals import hulk_id, hulk_sk, hulk_meta, hulk_profile

#
#  Configurations
#
from etc.cfg_db import base_dir
from etc.cfg_gsp import station_id
from etc.cfg_chatbots import load_robot_info
from etc.cfg_chatbots import tuling_keys, tuling_ignores, xiaoi_keys, xiaoi_ignores
from etc.cfg_chatbots import lingling_id, xiaoxiao_id


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
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    A map for short name to ID, just like DNS
"""
g_ans = AddressNameService()
g_ans.database = g_database


"""
    Messenger
    ~~~~~~~~~
"""
g_messenger = Messenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
station_id = g_facebook.identifier(station_id)

station_host = '127.0.0.1'
# station_host = '124.156.108.150'  # dimchat-hk
# station_host = '134.175.87.98'  # dimchat-gz
station_port = 9394

g_station = Station(identifier=station_id, host=station_host, port=station_port)
g_facebook.cache_user(user=g_station)


"""
    Chat Bots
    ~~~~~~~~~

    Chat bots for station
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


"""
    Local Robot
    ~~~~~~~~~~~
    
    Robot as a daemon
"""


class Daemon(Robot):

    def __init__(self, identifier: ID):
        super().__init__(identifier=identifier)
        # station connection
        self.delegate = g_facebook
        self.messenger = g_messenger
        # real chat bot
        self.bot: ChatBot = None

    def disconnect(self) -> bool:
        if g_messenger.delegate == self.connection:
            g_messenger.delegate = None
        return super().disconnect()

    def connect(self, station: Station) -> bool:
        if not super().connect(station=station):
            self.error('failed to connect station: %s' % station)
            return False
        if g_messenger.delegate is None:
            g_messenger.delegate = self.connection
        self.info('connected to station: %s' % station)
        # handshake after connected
        sleep(0.5)
        self.info('%s is shaking hands with %s' % (self.identifier, station))
        return self.handshake()

    def receive_message(self, msg: InstantMessage) -> bool:
        if super().receive_message(msg=msg):
            return True
        sender = g_facebook.identifier(msg.envelope.sender)
        if sender.type.is_robot():
            # ignore message from another robot
            return True
        content: Content = msg.content
        if isinstance(content, TextContent):
            # dialog
            question = content.text
            answer = self.bot.ask(question=question, user=str(sender.number))
            if answer is None:
                return False
            group = content.group
            text = TextContent.new(text=answer)
            if group is None:
                return self.send_content(content=text, receiver=sender)
            else:
                group = g_facebook.identifier(group)
                return self.send_content(content=text, receiver=group)


def create_daemon(identifier: str) -> Daemon:
    identifier = g_facebook.identifier(identifier)
    # check meta
    meta = g_facebook.meta(identifier=identifier)
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
        elif not g_facebook.save_private_key(private_key=private_key, identifier=identifier):
            raise AssertionError('failed to save private key for ID: %s, %s' % (identifier, private_key))
    if private_key is None:
        raise AssertionError('private key not found for ID: %s' % identifier)
    # check profile
    profile = load_robot_info(identifier=identifier, filename='profile.js')
    if profile is None:
        raise LookupError('failed to get profile for robot: %s' % identifier)
    Log.info('robot profile: %s' % profile)
    name = profile.get('name')
    # create profile
    profile = Profile.new(identifier=identifier)
    profile.set_property('name', name)
    profile.sign(private_key=private_key)
    if not g_facebook.save_profile(profile):
        raise AssertionError('failed to save profile: %s' % profile)
    # create robot
    robot = Daemon(identifier=identifier)
    g_facebook.cache_user(user=robot)
    Log.info('robot loaded: %s' % robot)
    return robot


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

Log.info('Chat bot: %s' % lingling_id)
Log.info('Chat bot: %s' % xiaoxiao_id)

Log.info('======== configuration OK!')
