# -*- coding: utf-8 -*-

import os

from libs.utils import Log
from libs.database import Storage

etc = os.path.abspath(os.path.dirname(__file__))


"""
    Log Level
    ~~~~~~~~~
"""
# Log.LEVEL = Log.DEBUG
Log.LEVEL = Log.DEVELOP
# Log.LEVEL = Log.RELEASE


"""
    Genesis Service Provider
    ~~~~~~~~~~~~~~~~~~~~~~~~

    Configuration of stations
"""
gsp_conf = os.path.join(etc, 'gsp.js')

bind_host = '0.0.0.0'
bind_port = 9394

local_host = '127.0.0.1'
local_port = 9394

station_id = None  # use the 'ID' value of first record of 'stations' in 'gsp.js' as default
# station_id = 'gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC'
# station_id = 'gsp-s002@wpjUWg1oYDnkHh74tHQFPxii6q9j3ymnyW'
# station_id = 'gsp-india@x15NniVboopEtD3d81cbUibftcewMxzZLw'
# station_id = 'gsp-jlp@x8Eudmgq4rHvTm2ongrwk6BVdS1wuE7ctE'
# station_id = 'gsp-yjd@wjPLYSyaZ7fe4aNL8DJAvHBNnFcgK76eYq'


"""
    System Bots
    ~~~~~~~~~~~

    1. assistant: bot for group message
    2. archivist: bot for searching users
"""
assistant_id = None  # use the first record of 'assistants' in 'gsp.js' as default
archivist_id = None  # use the first record of 'archivists' in 'gsp.js' as default


"""
    Database Configuration
    ~~~~~~~~~~~~~~~~~~~~~~

    Paths for data files: "/data/.dim"
"""
base_dir = '/data/.dim'
# base_dir = '/var/dim'


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


"""
    Chat Bots Configuration
    ~~~~~~~~~~~~~~~~~~~~~~~

    Secret keys for AI chat bots
"""
tuling_keys = Storage.read_json(path=os.path.join(etc, 'tuling', 'secret.js'))
tuling_ignores = [4003]

xiaoi_keys = Storage.read_json(path=os.path.join(etc, 'xiaoi', 'secret.js'))
xiaoi_ignores = ['默认回复', '重复回复']


"""
    Address Name Service
    ~~~~~~~~~~~~~~~~~~~~

    ANS reserved records
"""
ans_reserved_records = {
    'founder': 'moky@4DnqXWdTV8wuZgfqSCX9GjE2kNq7HJrUgQ',
    'moky': 'moky@4DnqXWdTV8wuZgfqSCX9GjE2kNq7HJrUgQ',
    'moki': 'moki@4WDfe3zZ4T7opFSi3iDAKiuTnUHjxmXekk',
    'hulk': 'hulk@4YeVEN3aUnvC1DNUufCq1bs9zoBSJTzVEj',
}
