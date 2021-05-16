# -*- coding: utf-8 -*-

import os

from libs.common import Storage

etc = os.path.abspath(os.path.dirname(__file__))


"""
    Genesis Service Provider
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Configuration of stations
"""
station_name = 'Genesis Station (GZ)'
station_host = '0.0.0.0'
station_port = 9394

# station_id = 'gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC'
station_id = 'gsp-s002@wpjUWg1oYDnkHh74tHQFPxii6q9j3ymnyW'

all_stations = [
    station_id,
    # {'ID': 'gsp-s002@wpjUWg1oYDnkHh74tHQFPxii6q9j3ymnyW', 'host': '106.52.25.169', 'port': 9394},
    {'ID': 'gsp-jlp@x8Eudmgq4rHvTm2ongrwk6BVdS1wuE7ctE', 'host': '47.254.237.224', 'port': 9394},
    {'ID': 'gsp-yjd@wjPLYSyaZ7fe4aNL8DJAvHBNnFcgK76eYq', 'host': '149.129.234.145', 'port': 9394},
    {'ID': 'gsp-india@x15NniVboopEtD3d81cbUibftcewMxzZLw', 'host': '147.139.30.182', 'port': 9394},
]

local_servers = [
    station_id,
]


"""
    System Bots Configuration
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    1. assistant: bot for group message
    2. archivist: bot for searching users
"""
archivist_id = 'archivist@2PVvMPm1j74HFWAGnDSZFkLsbEgM3KCGkTR'
assistant_id = 'assistant@2PpB6iscuBjA15oTjAsiswoX9qis5V3c1Dq'

group_assistants = [
    assistant_id,
    # 'assistant@4WBSiDzg9cpZGPqFrQ4bHcq4U5z9QAQLHS',
]


"""
    Chat Bots Configuration
    ~~~~~~~~~~~~~~~~~~~~~~~

    Secret keys for AI chat bots
"""
tuling_keys = Storage.read_json(path=os.path.join(etc, 'tuling', 'secret.js'))
tuling_ignores = [4003]

xiaoi_keys = Storage.read_json(path=os.path.join(etc, 'xiaoi', 'secret.js'))
xiaoi_ignores = ['默认回复', '重复回复']

xiaoxiao_id = 'xiaoxiao@2PhVByg7PhEtYPNzW5ALk9ygf6wop1gTccp'  # chat bot XiaoI
lingling_id = 'lingling@2PemMVAvxpuVZw2SYwwo11iBBEBb7gCvDHa'  # chat bot: Tuling

chatroom_id = 'chatroom-admin@2Pc5gJrEQYoz9D9TJrL35sA3wvprNdenPi7'


"""
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    ANS reserved records
"""
ans_reserved_records = {
    'founder': 'moky@4DnqXWdTV8wuZgfqSCX9GjE2kNq7HJrUgQ',

    'assistant': assistant_id,
    'archivist': archivist_id,

    # chat bots
    'xiaoxiao': xiaoxiao_id,
    'lingling': lingling_id,
    'chatroom': chatroom_id,

    # others
    'moky': 'moky@4DnqXWdTV8wuZgfqSCX9GjE2kNq7HJrUgQ',
    'moki': 'moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk',
    'hulk': 'hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj',
}


"""
    Database Configuration
    ~~~~~~~~~~~~~~~~~~~~~~

    Paths for data files: "/data/.dim"
"""
base_dir = '/data/.dim'


"""
    Apple Push Notification service
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Paths for APNs credentials: "/srv/dims/etc/apns/credentials.pem"
"""
apns_credentials = os.path.join(etc, 'apns', 'credentials.pem')
if not os.path.exists(apns_credentials):
    apns_credentials = None

apns_use_sandbox = False
apns_topic = 'chat.dim.client'
