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

from libs.utils.log import Log
from libs.server import ServerMessenger

#
#  Configurations
#
from etc.config import bind_host, bind_port

from etc.cfg_init import g_facebook
from etc.cfg_init import station_id, create_station


"""
    Messenger
    ~~~~~~~~~

    Transceiver for processing messages
"""
g_messenger = ServerMessenger(facebook=g_facebook)
g_facebook.messenger = g_messenger


"""
    Local Station
    ~~~~~~~~~~~~~
"""
Log.info('-------- Creating local server: %s (%s:%d)' % (station_id, bind_host, bind_port))
g_station = create_station(info={
    'ID': station_id,
    'host': bind_host,
    'port': bind_port
})
assert g_station is not None, 'current station not created: %s' % station_id
decrypt_keys = g_facebook.private_keys_for_decryption(identifier=station_id)
assert len(decrypt_keys) > 0, 'failed to get decrypt keys for current station: %s' % station_id
Log.info('Current station with %d private key(s): %s' % (len(decrypt_keys), g_station))

# set local users for facebook
g_facebook.local_users = [g_station]
g_facebook.current_user = g_station

Log.info('======== configuration OK! ========')
