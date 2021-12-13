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

import threading
import traceback
from typing import Union

from startrek.fsm import Runner
from startrek import DeparturePriority

from dimp import ReliableMessage

from libs.utils.log import Log
from libs.utils.ipc import ShuttleBus, ReceptionistArrows, MonitorArrow
from libs.utils import Singleton
from libs.utils import Notification, NotificationObserver, NotificationCenter
from libs.common import NotificationNames
from libs.server import ServerMessenger
from libs.server import SessionServer

#
#  Configurations
#
from etc.config import bind_host, bind_port

from etc.cfg_init import g_facebook, g_keystore
from etc.cfg_init import station_id, create_station


@Singleton
class ReceptionistCaller(Runner):
    """ handling 'handshake' commands """

    def __init__(self):
        super().__init__()
        self.__ss = SessionServer()
        # pipe
        bus = ShuttleBus()
        bus.set_arrows(arrows=ReceptionistArrows.primary(delegate=bus))
        threading.Thread(target=bus.run, daemon=True).start()
        self.__bus: ShuttleBus[dict] = bus
        threading.Thread(target=self.run, daemon=True).start()

    def send(self, msg: Union[dict, ReliableMessage]):
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        self.__bus.send(obj=msg)

    # Override
    def process(self) -> bool:
        obj = self.__bus.receive()
        if obj is None:
            return False
        try:
            return self.__try_process(obj=obj)
        except Exception as error:
            self.error(msg='failed to process: %s, %s' % (error, obj))
            traceback.print_exc()

    def __try_process(self, obj: dict) -> bool:
        msg = ReliableMessage.parse(msg=obj)
        assert msg is not None, 'msg error: %s' % obj
        sessions = self.__ss.active_sessions(identifier=msg.receiver)
        # check remote address
        remote = msg.get('remote')
        if remote is None:
            # push to all active sessions
            for sess in sessions:
                sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)
        else:
            # push to active session with same remote address
            msg.pop('remote')
            for sess in sessions:
                if sess.remote_address == remote:
                    sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)
        return True


@Singleton
class MonitorCaller(NotificationObserver):
    """ handling user events """

    def __init__(self):
        super().__init__()
        self.__outgo_arrow = MonitorArrow.primary()
        # observing local notifications
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)
        nc.add(observer=self, name=NotificationNames.USER_OFFLINE)
        nc.add(observer=self, name=NotificationNames.DELIVER_MESSAGE)

    # Override
    def received_notification(self, notification: Notification):
        name = notification.name
        info = notification.info
        self.__outgo_arrow.send(obj={
            'name': name,
            'info': info,
        })
        ReceptionistCaller().send(msg={
            'name': name,
            'info': info,
        })


"""
    Messenger
    ~~~~~~~~~

    Transceiver for processing messages
"""
g_messenger = ServerMessenger()
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
# set current station for key store
g_keystore.user = g_station

Log.info('======== configuration OK! ========')
