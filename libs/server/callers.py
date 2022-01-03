# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    IPC Callers
    ~~~~~~~~~~~

"""

import threading
import time
import traceback
from typing import Union, Optional

from startrek.fsm import Runner
from startrek import DeparturePriority

from dimp import ReliableMessage
from dimsdk import Station

from ..utils.log import Logging
from ..utils.ipc import ReceptionistPipe, ArchivistPipe, OctopusPipe, MonitorPipe
from ..utils import Notification, NotificationObserver, NotificationCenter
from ..utils import Singleton
from ..database import Database
from ..common import SharedFacebook, CommonMessenger, NotificationNames

from .session_server import SessionServer


g_session_server = SessionServer()
g_facebook = SharedFacebook()
g_database = Database()


def current_station() -> Optional[Station]:
    station = g_facebook.current_user
    if station is None:
        station = OctopusCaller().station
    return station


@Singleton
class ReceptionistCaller(Runner, Logging, NotificationObserver):
    """ call for offline messages """

    def __init__(self):
        super().__init__()
        self.__dispatcher = None
        self.__pipe = ReceptionistPipe.primary()
        self.start()
        # observing local notifications
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)

    @property
    def dispatcher(self):
        if self.__dispatcher is None:
            from libs.server import Dispatcher
            self.__dispatcher = Dispatcher()
        return self.__dispatcher

    # Override
    def received_notification(self, notification: Notification):
        self.__pipe.send(obj={
            'name': notification.name,
            'info': notification.info,
        })

    def start(self):
        self.__pipe.start()
        threading.Thread(target=self.run, daemon=True).start()

    # Override
    def stop(self):
        self.__pipe.stop()
        super().stop()

    # Override
    def process(self) -> bool:
        obj = None
        try:
            obj = self.__pipe.receive()
            if obj is not None:
                msg = ReliableMessage.parse(msg=obj)
                assert msg is not None, 'message error: %s' % obj
                client_address = msg.get('client_address')
                msg.pop('client_address', None)
                if isinstance(client_address, list):
                    client_address = (client_address[0], client_address[1])
                self.dispatcher.deliver(msg=msg, client_address=client_address)
                return True
        except Exception as error:
            self.error(msg='failed to process: %s, %s' % (error, obj))
            traceback.print_exc()


@Singleton
class SearchEngineCaller(Runner, Logging):
    """ handling 'search' command """

    def __init__(self):
        super().__init__()
        self.__ss = SessionServer()
        self.__pipe = ArchivistPipe.primary()
        self.__next_time = 0
        self.start()

    def start(self):
        self.__pipe.start()
        threading.Thread(target=self.run, daemon=True).start()

    # Override
    def stop(self):
        self.__pipe.stop()
        super().stop()

    def send(self, msg: Union[dict, ReliableMessage]) -> int:
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        return self.__pipe.send(obj=msg)

    # Override
    def process(self) -> bool:
        obj = None
        try:
            obj = self.__pipe.receive()
            if obj is None:
                now = time.time()
                if now > self.__next_time:
                    self.__next_time = now + 180
                    self.__update_online_users()
                return False
            msg = ReliableMessage.parse(msg=obj)
            client_address = msg.get('client_address')
            msg.pop('client_address', None)
            if isinstance(client_address, list):
                client_address = (client_address[0], client_address[1])
            self.__deliver_message(msg=msg, client_address=client_address)
            return True
        except Exception as error:
            self.error(msg='search engine error: %s, %s' % (error, obj))
            traceback.print_exc()

    def __update_online_users(self):
        station = current_station()
        if station is None:
            return False
        sid = station.identifier
        users = g_session_server.active_users(start=0, limit=-1)
        self.info(msg='update online users in %s: %s' % (sid, users))
        for item in users:
            g_database.add_online_user(station=sid, user=item)

    def __deliver_message(self, msg: ReliableMessage, client_address: Optional[tuple]):
        sessions = self.__ss.active_sessions(identifier=msg.receiver)
        self.debug(msg='received from search engine for %s (%d sessions)' % (msg.receiver, len(sessions)))
        # check remote address
        if client_address is None:
            # push to all active sessions
            for sess in sessions:
                sess.send_reliable_message(msg=msg, priority=DeparturePriority.NORMAL)
        else:
            # push to active session with same remote address
            for sess in sessions:
                if sess.client_address == client_address:
                    sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)


@Singleton
class OctopusCaller(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__dispatcher = None
        self.__pipe = OctopusPipe.primary()
        self.start()

    @property
    def dispatcher(self):
        if self.__dispatcher is None:
            from libs.server import Dispatcher
            self.__dispatcher = Dispatcher()
        return self.__dispatcher

    def start(self):
        self.__pipe.start()
        threading.Thread(target=self.run, daemon=True).start()

    # Override
    def stop(self):
        self.__pipe.stop()
        super().stop()

    def send(self, msg: Union[dict, ReliableMessage]) -> int:
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        return self.__pipe.send(obj=msg)

    # Override
    def process(self) -> bool:
        messenger = g_facebook.messenger
        if not isinstance(messenger, CommonMessenger):
            self.error(msg='messenger not set yet')
            return False
        obj = None
        try:
            obj = self.__pipe.receive()
            if obj is None:
                return False
            msg = ReliableMessage.parse(msg=obj)
            assert msg is not None, 'message error: %s' % obj
            messenger.process_reliable_message(msg=msg)
            return True
        except Exception as error:
            self.error(msg='failed to process: %s, %s' % (error, obj))
            traceback.print_exc()


@Singleton
class MonitorCaller(NotificationObserver):
    """ handling user events """

    def __init__(self):
        super().__init__()
        self.__pipe = MonitorPipe.primary()
        self.__pipe.start()
        # observing local notifications
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)
        nc.add(observer=self, name=NotificationNames.USER_OFFLINE)
        nc.add(observer=self, name=NotificationNames.DELIVER_MESSAGE)

    # Override
    def received_notification(self, notification: Notification):
        event = {
            'name': notification.name,
            'info': notification.info,
        }
        self.__pipe.send(obj=event)
