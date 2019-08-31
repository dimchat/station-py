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

from common import g_keystore, g_database, g_facebook, load_accounts, Log
from common import s001, s001_host, s001_port

from .session import SessionServer
from .apns import ApplePushNotificationService
from .dispatcher import Dispatcher

from .receptionist import Receptionist
from .monitor import Monitor
from .gsp_admins import administrators


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
current_station = s001
station_host = s001_host
station_port = s001_port


"""
    Key Store
    ~~~~~~~~~

    Memory cache for reused passwords (symmetric key)
"""
g_keystore.user = current_station


"""
    Database
    ~~~~~~~~

    for cached messages, profile manage(Barrack), reused symmetric keys(KeyStore)
"""
# g_database.base_dir = '/data/.dim/'
Log.info("database directory: %s" % g_database.base_dir)


"""
    Facebook
    ~~~~~~~~

    Barrack for cache entities
"""
load_accounts(facebook=g_facebook)


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
g_receptionist.apns = g_apns
g_receptionist.station = current_station
