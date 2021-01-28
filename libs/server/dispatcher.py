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
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""

import time
import threading
import traceback
from threading import Thread
from typing import Optional, Union, List, Set

from dimp import ID, NetworkType
from dimp import ReliableMessage
from dimp import ContentType, Content, TextContent
from dimsdk import Station
from dimsdk import ReceiptCommand

from libs.utils import Log, Singleton
from libs.utils import Notification, NotificationObserver, NotificationCenter
from libs.common import NotificationNames
from libs.common import Database

from .push_message_service import PushMessageService
from .session import Session, SessionServer
from .facebook import ServerFacebook


@Singleton
class Dispatcher(Thread, NotificationObserver):

    def __init__(self):
        super().__init__()
        self.__running = True
        self.__station: Optional[ID] = None
        # self.apns: ApplePushNotificationService = None
        self.__push_service = PushMessageService()
        self.__neighbors: List[ID] = []     # ID list
        self.__waiting_list: List[ReliableMessage] = []  # ReliableMessage list
        self.__waiting_list_lock = threading.Lock()
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.DISCONNECTED)
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)

    def __del__(self):
        nc = NotificationCenter()
        nc.remove(observer=self, name=NotificationNames.DISCONNECTED)
        nc.remove(observer=self, name=NotificationNames.USER_LOGIN)

    def debug(self, msg: str):
        Log.debug('%s >\t%s' % (self.__class__.__name__, msg))

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def warning(self, msg: str):
        Log.warning('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def station(self) -> ID:
        return self.__station

    @station.setter
    def station(self, server: Union[ID, Station]):
        if isinstance(server, Station):
            server = server.identifier
        self.__station = server

    def push(self, sender: ID, receiver: ID, message: str) -> bool:
        self.__push_service.push(sender=sender, receiver=receiver, message=message)
        return True

    #
    #    Notification Observer
    #
    def received_notification(self, notification: Notification):
        name = notification.name
        info = notification.info
        if name == NotificationNames.DISCONNECTED:
            session = info.get('session')
            if isinstance(session, Session):
                identifier = session.identifier
                if identifier is not None and identifier.type == NetworkType.STATION:
                    self.remove_neighbor(station=identifier)
        elif name == NotificationNames.USER_LOGIN:
            identifier = info.get('ID')
            if identifier is not None and identifier.type == NetworkType.STATION:
                self.add_neighbor(station=identifier)

    @property
    def session_server(self) -> SessionServer:
        return SessionServer()

    @property
    def facebook(self) -> ServerFacebook:
        return ServerFacebook()

    @property
    def database(self) -> Database:
        return self.facebook.database

    def add_neighbor(self, station: Union[Station, ID]) -> bool:
        if isinstance(station, Station):
            station = station.identifier
        else:
            assert isinstance(station, ID), 'station ID error: %s' % station
        if station == self.station:
            return False
        # FIXME: thread safe
        if station in self.__neighbors:
            return False
        self.__neighbors.append(station)
        return True

    def remove_neighbor(self, station: Union[Station, ID]):
        if isinstance(station, Station):
            station = station.identifier
        else:
            assert isinstance(station, ID), 'station ID error: %s' % station
        # FIXME: thread safe
        if station in self.__neighbors:
            self.__neighbors.remove(station)

    def __add_msg(self, msg: ReliableMessage):
        with self.__waiting_list_lock:
            self.__waiting_list.append(msg)

    def __pop_msg(self) -> Optional[ReliableMessage]:
        with self.__waiting_list_lock:
            if len(self.__waiting_list) > 0:
                return self.__waiting_list.pop(0)

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        self.__add_msg(msg=msg)
        # response
        return self.__receipt(message='Message delivering', msg=msg)

    @staticmethod
    def __receipt(message: str, msg: ReliableMessage) -> Content:
        receipt = ReceiptCommand(message=message)
        for key in ['sender', 'receiver', 'time', 'group', 'signature']:
            value = msg.get(key)
            if value is not None:
                receipt[key] = value
        return receipt

    def __traced(self, msg: ReliableMessage, station: ID) -> bool:
        traces = msg.get('traces')
        if traces is None:
            # broadcast message starts from here
            traces = [station]
        else:
            for node in traces:
                if isinstance(node, str):
                    if station == node:
                        return True
                elif isinstance(node, dict):
                    if station == node.get('ID'):
                        return True
                else:
                    self.error('traces node error: %s' % node)
            # broadcast message go through here
            traces.append(station)
        msg['traces'] = ID.revert(members=traces)
        return False

    def __broadcast_message(self, msg: ReliableMessage) -> Optional[Content]:
        """ Deliver message to everyone@everywhere, including all neighbours """
        self.debug('broadcasting message from: %s' % msg.sender)
        if self.__traced(msg=msg, station=self.station):
            self.error('ignore traced msg: %s in %s' % (self.station, msg.get('traces')))
            return None
        session_server = self.session_server
        # push to all neighbors connected th current station
        neighbors = self.__neighbors.copy()
        sent_neighbors = []
        success = 0
        for sid in neighbors:
            if sid == self.station:
                continue
            sessions = session_server.active_sessions(identifier=sid)
            if len(sessions) == 0:
                self.warning('remote station (%s) not connected, try later.' % sid)
                continue
            if self.__push_message(msg=msg, receiver=sid, sessions=sessions):
                sent_neighbors.append(sid)
                success += 1
        # push to the bridge (octopus) of current station
        sid = self.station
        sessions = session_server.active_sessions(identifier=sid)
        if len(sessions) > 0:
            # tell the bridge ignore this neighbor stations
            sent_neighbors.append(sid)
            msg['sent_neighbors'] = ID.revert(sent_neighbors)
            self.__push_message(msg=msg, receiver=sid, sessions=sessions)
        # FIXME: what about the failures
        # response
        text = 'Message broadcast to %d/%d stations' % (success, len(neighbors))
        res = TextContent(text=text)
        res.group = msg.group
        return res
        # return None

    def __push_message(self, msg: ReliableMessage, receiver: ID, sessions: Set[Session]) -> bool:
        self.debug('%s is online(%d), try to push message for: %s' % (receiver, len(sessions), msg.sender))
        success = 0
        for sess in sessions:
            if sess.push_message(msg):
                success = success + 1
            else:
                self.error('failed to push message via connection (%s, %s)' % sess.client_address)
        if success > 0:
            self.debug('message for user %s pushed to %d sessions' % (receiver, success))
            return True

    def __redirect_message(self, msg: ReliableMessage, receiver: ID, neighbor: ID) -> bool:
        self.debug('%s is roaming, try to redirect: %s' % (receiver, neighbor))
        sessions = self.session_server.active_sessions(identifier=neighbor)
        if len(sessions) == 0:
            self.debug('remote station (%s) not connected, trying bridge...' % neighbor)
            neighbor = self.station
            sessions = self.session_server.active_sessions(identifier=neighbor)
            if len(sessions) == 0:
                self.error('station bridge (%s) not connected, cannot redirect.' % neighbor)
                return False
        if self.__push_message(msg=msg, receiver=neighbor, sessions=sessions):
            self.debug('message for user %s redirected to %s' % (receiver, neighbor))
            return True

    def __roaming(self, receiver: ID) -> Optional[ID]:
        login = self.database.login_command(identifier=receiver)
        if login is None:
            return None
        station = login.station
        if station is None:
            return None
        # check time expires
        now = time.time()
        login_time = login.time
        if login_time is None:
            self.error('%s login time not set: %s' % (receiver, login))
            return None
        if (now - login_time) > (3600 * 24 * 7):
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(login_time))
            self.debug('%s login expired: [%s] %s' % (receiver, t_str, login))
            return None
        sid = ID.parse(identifier=station.get('ID'))
        if sid == self.station:
            return None
        return sid

    def __push_notification(self, sender: ID, receiver: ID, group: ID, msg_type: int = 0) -> bool:
        if msg_type == 0:
            something = 'a message'
        elif msg_type == ContentType.TEXT:
            something = 'a text message'
        elif msg_type == ContentType.FILE:
            something = 'a file'
        elif msg_type == ContentType.IMAGE:
            something = 'an image'
        elif msg_type == ContentType.AUDIO:
            something = 'a voice message'
        elif msg_type == ContentType.VIDEO:
            something = 'a video'
        else:
            self.debug('ignore msg type: %d' % msg_type)
            return False
        from_name = self.facebook.name(identifier=sender)
        to_name = self.facebook.name(identifier=receiver)
        text = 'Dear %s: %s sent you %s' % (to_name, from_name, something)
        # check group
        if group is not None:
            # group message
            text += ' in group [%s]' % self.facebook.name(identifier=group)
        # push it
        self.info('APNs message: %s' % text)
        # return self.apns.push(identifier=receiver, message=text)
        return self.push(sender=sender, receiver=receiver, message=text)

    def __deliver(self, msg: ReliableMessage) -> Optional[Content]:
        # check receiver
        receiver = msg.receiver
        if receiver.is_group:
            # group message (not split yet)
            if receiver.is_broadcast:
                # if it's a grouped broadcast message, then
                #    broadcast (split and deliver) to everyone
                return self.__broadcast_message(msg=msg)
            else:
                # let the assistant to process this group message
                assistants = self.facebook.assistants(receiver)
                if assistants is None or len(assistants) == 0:
                    raise LookupError('failed to get assistant for group: %s' % receiver)
                receiver = assistants[0]
        # check online sessions
        sessions = self.session_server.active_sessions(identifier=receiver)
        if len(sessions) == 0:
            # check roaming station
            neighbor = self.__roaming(receiver=receiver)
            if neighbor is not None:
                # redirect message to the roaming station
                if self.__redirect_message(msg=msg, receiver=receiver, neighbor=neighbor):
                    return self.__receipt(message='Message redirected', msg=msg)
        elif self.__push_message(msg=msg, receiver=receiver, sessions=sessions):
            return self.__receipt(message='Message sent', msg=msg)
        # store in local cache file
        sender = msg.sender
        group = msg.group

        self.debug('%s is offline, store message from: %s' % (receiver, sender))
        self.database.store_message(msg)
        # check mute-list
        if self.database.is_muted(sender=sender, receiver=receiver, group=group):
            self.info('this sender/group is muted: %s' % msg)
        else:
            # push notification
            msg_type = msg.type
            if msg_type is None:
                msg_type = 0
            self.__push_notification(sender=sender, receiver=receiver, group=group, msg_type=msg_type)

    #
    #   Run Loop
    #
    def __run_unsafe(self):
        while True:
            msg = self.__pop_msg()
            if msg is None:
                break
            res = self.__deliver(msg=msg)
            if res is not None:
                # TODO: respond the deliver result to the sender
                pass

    def run(self):
        self.info('dispatcher starting...')
        while self.__running:
            # noinspection PyBroadException
            try:
                self.__run_unsafe()
            except Exception as error:
                self.error('dispatcher error: %s' % error)
                traceback.print_exc()
            finally:
                # sleep for next loop
                time.sleep(0.1)
        self.info('dispatcher exit!')

    def stop(self):
        self.__running = False
