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
import traceback
from typing import Union

from startrek.fsm import Runner
from startrek import DeparturePriority

from dimp import ID, ReliableMessage

from ..utils.log import Logging
from ..utils.ipc import ShuttleBus, ReceptionistArrows, ArchivistArrows, OctopusArrows, MonitorArrow
from ..utils import Notification, NotificationObserver, NotificationCenter
from ..utils import Singleton
from ..database import Database
from ..common import SharedFacebook, NotificationNames

from .session import SessionServer


g_session_server = SessionServer()
g_facebook = SharedFacebook()
g_database = Database()


@Singleton
class ReceptionistCaller(Runner, Logging):
    """ handling 'handshake' commands """

    def __init__(self):
        super().__init__()
        self.__ss = SessionServer()
        # pipe
        bus = ShuttleBus()
        bus.set_arrows(arrows=ReceptionistArrows.primary(delegate=bus))
        bus.start()
        self.__bus: ShuttleBus[dict] = bus
        threading.Thread(target=self.run, daemon=True).start()

    def send(self, msg: Union[dict, ReliableMessage]):
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        self.__bus.send(obj=msg)

    # Override
    def process(self) -> bool:
        obj = None
        try:
            obj = self.__bus.receive()
            if obj is None:
                return False
            if 'command' in obj:
                identifier = ID.parse(identifier=obj['ID'])
                client_address = obj['client_address']
                session_key = obj['session_key']
                self.__update_session(identifier=identifier, address=client_address, key=session_key)
            else:
                msg = ReliableMessage.parse(msg=obj)
                self.__deliver_message(msg=msg)
            return True
        except Exception as error:
            self.error(msg='failed to process: %s, %s' % (error, obj))
            traceback.print_exc()

    def __update_session(self, identifier: ID, address: tuple, key: str):
        session = self.__ss.get_session(client_address=address)
        if session is not None:
            assert key == session.key, 'session keys not match %s: %s, %s' % (identifier, key, session.key)
            session.active = True
            self.__ss.update_session(session=session, identifier=identifier)

    def __deliver_message(self, msg: ReliableMessage):
        sessions = self.__ss.active_sessions(identifier=msg.receiver)
        # check remote address
        remote = msg.get('client_address')
        if remote is None:
            # push to all active sessions
            for sess in sessions:
                sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)
        else:
            # push to active session with same remote address
            msg.pop('client_address')
            for sess in sessions:
                if sess.remote_address == remote:
                    sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)


@Singleton
class SearchEngineCaller(Runner, Logging):
    """ handling 'search' command """

    def __init__(self):
        super().__init__()
        self.__ss = SessionServer()
        # pipe
        bus = ShuttleBus()
        bus.set_arrows(arrows=ArchivistArrows.primary(delegate=bus))
        bus.start()
        self.__bus: ShuttleBus[dict] = bus
        threading.Thread(target=self.run, daemon=True).start()

    def send(self, msg: Union[dict, ReliableMessage]):
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        self.__bus.send(obj=msg)

    # Override
    def process(self) -> bool:
        obj = None
        try:
            obj = self.__bus.receive()
            if obj is None:
                return False
            msg = ReliableMessage.parse(msg=obj)
            self.__deliver_message(msg=msg)
            return self.__try_process(obj=obj)
        except Exception as error:
            self.error(msg='search engine error: %s, %s' % (error, obj))
            traceback.print_exc()

    def __deliver_message(self, msg: ReliableMessage):
        sessions = self.__ss.active_sessions(identifier=msg.receiver)
        self.debug(msg='received from search engine for %s (%d sessions)' % (msg.receiver, len(sessions)))
        # check remote address
        remote = msg.get('client_address')
        if remote is None:
            # push to all active sessions
            for sess in sessions:
                sess.send_reliable_message(msg=msg, priority=DeparturePriority.NORMAL)
        else:
            # push to active session with same remote address
            msg.pop('client_address')
            for sess in sessions:
                if sess.remote_address == remote:
                    sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)
        return True


@Singleton
class OctopusCaller(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__ss = SessionServer()
        # pipe
        bus = ShuttleBus()
        bus.set_arrows(arrows=OctopusArrows.primary(delegate=bus))
        bus.start()
        self.__bus: ShuttleBus[dict] = bus
        threading.Thread(target=self.run, daemon=True).start()

    def send(self, msg: Union[dict, ReliableMessage]):
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        self.__bus.send(obj=msg)

    # Override
    def process(self) -> bool:
        obj = None
        try:
            obj = self.__bus.receive()
            if obj is None:
                return False
            msg = ReliableMessage.parse(msg=obj)
            self.__deliver_message(msg=msg)
            return True
        except Exception as error:
            self.error(msg='failed to process: %s, %s' % (error, obj))
            traceback.print_exc()

    def __deliver_message(self, msg: ReliableMessage):
        sessions = self.__ss.active_sessions(identifier=msg.receiver)
        self.debug(msg='received from bridge for %s (%d sessions)' % (msg.receiver, len(sessions)))
        # push to all active sessions
        for sess in sessions:
            sess.send_reliable_message(msg=msg, priority=DeparturePriority.URGENT)


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
        event = {
            'name': notification.name,
            'info': notification.info,
        }
        self.__outgo_arrow.send(obj=event)
        ReceptionistCaller().send(msg=event)
