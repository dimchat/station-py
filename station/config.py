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

from ipx import Singleton
from ipx import NotificationObserver, Notification, NotificationCenter
from ipx import SharedMemoryArrow

#
#  Common Libs
#
from libs.utils import Log
from libs.push import PushCenter
from libs.common import NotificationNames
from libs.server import ServerMessenger
from libs.server import Dispatcher

#
#  Configurations
#
from etc.config import bind_host, bind_port

from etc.cfg_init import g_facebook, g_keystore
from etc.cfg_init import station_id, create_station, neighbor_stations


class MonitorArrow(SharedMemoryArrow):
    """ Half-duplex Pipe from station to pusher """

    # Station process IDs:
    #   0 - main
    #   1 - receptionist
    #   2 - pusher
    #   3 - monitor
    SHM_KEY = "D13503FF"

    # Memory cache size: 64KB
    SHM_SIZE = 1 << 16

    @classmethod
    def aim(cls):
        return cls.new(size=cls.SHM_SIZE, name=cls.SHM_KEY)


@Singleton
class Monitor(NotificationObserver):

    def __init__(self):
        super().__init__()
        self.__arrow = MonitorArrow.aim()
        # observing local notifications
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)
        nc.add(observer=self, name=NotificationNames.USER_OFFLINE)
        nc.add(observer=self, name=NotificationNames.DELIVER_MESSAGE)

    def __del__(self):
        nc = NotificationCenter()
        nc.remove(observer=self, name=NotificationNames.USER_LOGIN)
        nc.remove(observer=self, name=NotificationNames.USER_ONLINE)
        nc.remove(observer=self, name=NotificationNames.USER_OFFLINE)
        nc.remove(observer=self, name=NotificationNames.DELIVER_MESSAGE)

    # Override
    def received_notification(self, notification: Notification):
        self.__arrow.send(obj={
            'name': notification.name,
            'info': notification.info,
        })


"""
    Messenger
    ~~~~~~~~~

    Transceiver for processing messages
"""
g_messenger = ServerMessenger()
g_facebook.messenger = g_messenger


"""
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""
g_dispatcher = Dispatcher()
g_dispatcher.push_service = PushCenter()


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
# set current station for key store
g_keystore.user = g_station
# set current station for dispatcher
g_dispatcher.station = g_station.identifier

# load neighbour station for delivering message
Log.info('-------- Loading neighbor stations: %d' % len(neighbor_stations))
for node in neighbor_stations:
    assert node != g_station, 'neighbor station error: %s, %s' % (node, g_station)
    Log.info('add node: %s' % node)
    g_dispatcher.add_neighbor(station=node.identifier)

Log.info('======== configuration OK! ========')
