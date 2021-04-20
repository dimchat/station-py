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

from dimp import ID
from dimsdk.ans import keywords as ans_keywords

#
#  Common Libs
#
from libs.utils import Log
from libs.common import AddressNameServer
from libs.common import Storage
from libs.client import ClientMessenger, ClientFacebook
from libs.client import Server, Terminal, Connection

#
#  Configurations
#
from etc.cfg_db import base_dir, ans_reserved_records
from etc.cfg_gsp import station_id, all_stations
from etc.cfg_bots import group_assistants
from etc.cfg_bots import lingling_id, xiaoxiao_id, chatroom_id

from etc.cfg_loader import load_station


#
#  Log Level
#
# Log.LEVEL = Log.DEBUG
Log.LEVEL = Log.DEVELOP
# Log.LEVEL = Log.RELEASE


# data directory
Log.info("local storage directory: %s" % base_dir)
Storage.root = base_dir

"""
    Connection
    ~~~~~~~~~~
    time interval for maintaining connection
"""
Connection.HEARTBEAT_INTERVAL = 8


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
station_id = ID.parse(identifier=station_id)

station_host = '127.0.0.1'
# station_host = '106.52.25.169'  # dimchat-gz
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
    Client
    ~~~~~~
    
"""


def dims_connect(terminal: Terminal, server: Server, messenger: ClientMessenger) -> Terminal:
    messenger.delegate = server
    messenger.terminal = terminal
    server.messenger = messenger
    # client
    terminal.messenger = messenger
    terminal.start(server=server)
    # server.handshake()
    return terminal


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

# convert robot IDs
Log.info('-------- robots')

group_assistants = [ID.parse(identifier=item) for item in group_assistants]
Log.info('Group assistants: %s' % group_assistants)
g_facebook.group_assistants = group_assistants

lingling_id = ID.parse(identifier=lingling_id)
xiaoxiao_id = ID.parse(identifier=xiaoxiao_id)
chatroom_id = ID.parse(identifier=chatroom_id)

Log.info('Chat bot: %s' % lingling_id)
Log.info('Chat bot: %s' % xiaoxiao_id)
Log.info('Chatroom: %s' % chatroom_id)

Log.info('======== configuration OK!')
