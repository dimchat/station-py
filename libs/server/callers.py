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
from typing import Union

from startrek.fsm import Runner
from startrek import DeparturePriority

from dimp import ID, ReliableMessage
from dimsdk import Station

from ..utils.log import Log, Logging
from ..utils.ipc import AgentPipe, ArchivistPipe, OctopusPipe, MonitorPipe
from ..utils import Notification, NotificationObserver, NotificationCenter
from ..utils import Singleton
from ..database import Database
from ..common import SharedFacebook, NotificationNames

from .session import SessionServer


g_session_server = SessionServer()
g_facebook = SharedFacebook()
g_database = Database()


def update_online_users():
    station = g_facebook.current_user
    if station is None:
        station = OctopusCaller().station
        if station is None:
            return False
    sid = station.identifier
    users = g_session_server.active_users(start=0, limit=-1)
    Log.info(msg='update online users in %s: %s' % (sid, users))
    for item in users:
        g_database.add_online_user(station=sid, user=item)


@Singleton
class AgentCaller(Runner, Logging):
    """ handling 'handshake' commands """

    def __init__(self):
        super().__init__()
        self.__ss = SessionServer()
        self.__pipe = AgentPipe.primary()
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
                return False
            assert isinstance(obj, dict), 'piped object error: %s' % obj
            name = obj.get('name')
            info = obj.get('info')
            if name is not None and info is not None:
                self.__process_notification(name=name, info=info)
            else:
                msg = ReliableMessage.parse(msg=obj)
                self.__deliver_message(msg=msg)
            return True
        except Exception as error:
            self.error(msg='failed to process: %s, %s' % (error, obj))
            traceback.print_exc()

    def __process_notification(self, name: str, info: dict):
        self.debug(msg='notification: %s' % name)
        if name == NotificationNames.USER_LOGIN:
            identifier = ID.parse(identifier=info['ID'])
            client_address = info['client_address']
            key = info['session_key']
            assert identifier is not None, 'ID not found: %s' % info
            if client_address is not None and key is not None:
                client_address = (client_address[0], client_address[1])
                self.__update_session(identifier=identifier, address=client_address)
                return
        # post for monitor
        NotificationCenter().post(name=name, sender='agent', info=info)

    def __update_session(self, identifier: ID, address: tuple):
        session = self.__ss.get_session(address=address)
        if session is not None:
            session.active = True
            self.__ss.update_session(session=session, identifier=identifier)

    def __deliver_message(self, msg: ReliableMessage):
        # check remote address
        client_address = msg.get('client_address')
        if client_address is None:
            # push to all active sessions
            sessions = self.__ss.active_sessions(identifier=msg.receiver)
            for sess in sessions:
                sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)
        else:
            # push to active session with same remote address
            client_address = (client_address[0], client_address[1])
            sess = self.__ss.get_session(address=client_address)
            if sess is not None:
                msg.pop('client_address')
                sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)


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
                    self.__next_time = now + 300
                    update_online_users()
                return False
            msg = ReliableMessage.parse(msg=obj)
            self.__deliver_message(msg=msg)
            return True
        except Exception as error:
            self.error(msg='search engine error: %s, %s' % (error, obj))
            traceback.print_exc()

    def __deliver_message(self, msg: ReliableMessage):
        sessions = self.__ss.active_sessions(identifier=msg.receiver)
        self.debug(msg='received from search engine for %s (%d sessions)' % (msg.receiver, len(sessions)))
        # check remote address
        client_address = msg.get('client_address')
        if client_address is None:
            # push to all active sessions
            for sess in sessions:
                sess.send_reliable_message(msg=msg, priority=DeparturePriority.NORMAL)
        else:
            # push to active session with same remote address
            client_address = (client_address[0], client_address[1])
            msg.pop('client_address')
            for sess in sessions:
                if sess.client_address == client_address:
                    sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)


@Singleton
class OctopusCaller(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__ss = SessionServer()
        self.__station = None
        self.__pipe = OctopusPipe.primary()
        self.start()

    def start(self):
        self.__pipe.start()
        threading.Thread(target=self.run, daemon=True).start()

    # Override
    def stop(self):
        self.__pipe.stop()
        super().stop()

    @property
    def station(self) -> Station:
        return self.__station

    @station.setter
    def station(self, server: Station):
        self.__station = server

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
                return False
            msg = ReliableMessage.parse(msg=obj)
            self.__deliver_message(msg=msg)
            return True
        except Exception as error:
            self.error(msg='failed to process: %s, %s' % (error, obj))
            traceback.print_exc()

    def __deliver_message(self, msg: ReliableMessage):
        receiver = msg.receiver
        sessions = self.__ss.active_sessions(identifier=receiver)
        if len(sessions) > 0:
            self.debug(msg='received from bridge for %s (%d sessions)' % (receiver, len(sessions)))
            # push to all active sessions
            for sess in sessions:
                sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)
        elif receiver == self.station.identifier:
            self.debug(msg='received from bridge for station %s' % receiver)
            AgentCaller().send(msg=msg)
        elif receiver.is_broadcast:
            self.debug(msg='received broadcast from bridge: %s' % receiver)
            AgentCaller().send(msg=msg)


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
        AgentCaller().send(msg=event)
