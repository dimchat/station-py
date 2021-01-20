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

from dimp import Meta, ID
from dimsdk.ans import keywords as ans_keywords

#
#  Common Libs
#
from libs.utils import Log
from libs.utils.nlp import ChatBot, Tuling, XiaoI
from libs.common import AddressNameServer
from libs.common import Storage
from libs.client import Server, Terminal, ClientMessenger, ClientFacebook

#
#  Configurations
#
from etc.cfg_db import base_dir, ans_reserved_records
from etc.cfg_gsp import station_id, all_stations
from etc.cfg_bots import group_assistants
from etc.cfg_bots import group_naruto
from etc.cfg_bots import tuling_keys, tuling_ignores, xiaoi_keys, xiaoi_ignores
from etc.cfg_bots import lingling_id, xiaoxiao_id, chatroom_id, tokentalkteam_id

from etc.cfg_loader import load_robot_info, load_station

g_released = True

Log.info("local storage directory: %s" % base_dir)
Storage.root = base_dir


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
station_id = ID.parse(identifier=station_id)

station_host = '127.0.0.1'
# station_host = '134.175.87.98'  # dimchat-gz
# station_host = '124.156.108.150'  # dimchat-hk
station_port = 9394

g_station = Server(identifier=station_id, host=station_host, port=station_port)

g_facebook = ClientFacebook()
g_facebook.cache_user(user=g_station)

# Address Name Service
g_ans = AddressNameServer()
g_ans.save('station', g_station.identifier)
g_ans.save('moki', ID.parse(identifier='moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk'))
g_ans.save('hulk', ID.parse(identifier='hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj'))


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


def dims_connect(terminal: Terminal, server: Server, messenger: ClientMessenger) -> Terminal:
    # context
    messenger.context['station'] = server
    messenger.context['remote_address'] = (server.host, server.port)
    messenger.context['handshake_delegate'] = terminal
    messenger.delegate = server
    messenger.terminal = terminal
    # client
    terminal.messenger = messenger
    terminal.start(server=server)
    # start server
    server.messenger = messenger
    server.handshake()
    return terminal


"""
    Shodai Hokage
    ~~~~~~~~~~~~~
    
    A group contains all freshmen
"""


def load_naruto():
    gid = ID.parse(identifier=group_naruto)
    Log.info('naruto group: %s' % gid)
    meta = Meta.parse(meta=load_robot_info(gid, 'meta.js'))
    g_facebook.save_meta(identifier=gid, meta=meta)


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

# convert ID to Station
Log.info('-------- Loading stations: %d' % len(all_stations))
all_stations = [load_station(identifier=item, facebook=g_facebook) for item in all_stations]

# load group 'DIM Plaza'
Log.info('-------- Loading group contains all users')
load_naruto()

# convert robot IDs
Log.info('-------- robots')

group_assistants = [ID.parse(identifier=item) for item in group_assistants]
Log.info('Group assistants: %s' % group_assistants)
g_facebook.group_assistants = group_assistants

lingling_id = ID.parse(identifier=lingling_id)
xiaoxiao_id = ID.parse(identifier=xiaoxiao_id)
chatroom_id = ID.parse(identifier=chatroom_id)
tokentalkteam_id = ID.parse(identifier=tokentalkteam_id)

Log.info('Chat bot: %s' % lingling_id)
Log.info('Chat bot: %s' % xiaoxiao_id)
Log.info('Chat bot: %s' % tokentalkteam_id)
Log.info('Chatroom: %s' % chatroom_id)

Log.info('======== configuration OK!')
