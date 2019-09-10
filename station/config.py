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

from mkm.crypto.utils import base64_encode

from dimp import Profile

from common import Log
from common import Database, Facebook, KeyStore, Messenger
from common import ApplePushNotificationService, SessionServer

from common.immortals import moki_id, moki_name, moki_pk, moki_sk, moki_meta, moki_profile, moki
from common.immortals import hulk_id, hulk_name, hulk_pk, hulk_sk, hulk_meta, hulk_profile, hulk
from .cfg_gsp import s001_id, s001_name, s001_pk, s001_sk, s001_meta, s001_profile, s001
from .cfg_admins import administrators

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
current_station = s001
current_station.delegate = g_facebook
current_station.messenger = g_messenger

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

    Log.info('loading station: %s' % s001_id)
    facebook.save_meta(identifier=s001_id, meta=s001_meta)
    facebook.save_private_key(identifier=s001_id, private_key=s001_sk)
    facebook.save_profile(profile=s001_profile)

    # store station name
    profile = '{\"name\":\"%s\"}' % s001_name
    signature = base64_encode(s001_sk.sign(profile.encode('utf-8')))
    profile = {
        'ID': s001_id,
        'data': profile,
        'signature': signature,
    }
    profile = Profile(profile)
    facebook.save_profile(profile=profile)

    #
    # scan accounts
    #

    database.scan_ids()

    Log.info('======== loaded')
