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
import weakref
from abc import abstractmethod
from typing import Optional, List, Set

from dimp import NetworkType, ID, ANYONE, EVERYONE
from dimp import ReliableMessage
from dimp import ContentType, Content, TextContent

from ..utils import get_msg_sig
from ..utils import Singleton, Log, Logging
from ..utils import Notification, NotificationObserver, NotificationCenter
from ..push import PushService, build_message as build_push_message
from ..database import Database
from ..common import NotificationNames
from ..common import SharedFacebook
from ..common import msg_receipt, msg_traced

from .session import Session, SessionServer


g_session_server = SessionServer()
g_facebook = SharedFacebook()
g_database = Database()


@Singleton
class Dispatcher(NotificationObserver):

    def __init__(self):
        super().__init__()
        self.__single_worker = SingleDispatcher()
        self.__group_worker = GroupDispatcher()
        self.__broadcast_worker = BroadcastDispatcher()
        # Notifications
        self.__push_service: Optional[weakref.ReferenceType] = None
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.DISCONNECTED)
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)

    def __del__(self):
        self.__single_worker.stop()
        self.__single_worker = None
        self.__group_worker.stop()
        self.__group_worker = None
        self.__broadcast_worker.stop()
        self.__broadcast_worker = None
        nc = NotificationCenter()
        nc.remove(observer=self, name=NotificationNames.DISCONNECTED)
        nc.remove(observer=self, name=NotificationNames.USER_LOGIN)

    @property
    def push_service(self) -> Optional[PushService]:
        if self.__push_service is not None:
            return self.__push_service()

    @push_service.setter
    def push_service(self, service: PushService):
        self.__push_service = weakref.ref(service)

    def start(self):
        self.__single_worker.start()
        self.__group_worker.start()
        self.__broadcast_worker.start()

    def stop(self):
        self.__single_worker.stop()
        self.__group_worker.stop()
        self.__broadcast_worker.stop()

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
    def station(self) -> ID:
        return self.__single_worker.station

    @station.setter
    def station(self, server: ID):
        self.__single_worker.station = server
        self.__group_worker.station = server
        self.__broadcast_worker.station = server

    def add_neighbor(self, station: ID):
        self.__single_worker.add_neighbor(station=station)
        self.__group_worker.add_neighbor(station=station)
        self.__broadcast_worker.add_neighbor(station=station)

    def remove_neighbor(self, station: ID):
        self.__single_worker.remove_neighbor(station=station)
        self.__group_worker.remove_neighbor(station=station)
        self.__broadcast_worker.remove_neighbor(station=station)

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        # post notification for monitor
        NotificationCenter().post(name=NotificationNames.DELIVER_MESSAGE, sender=self, info=msg.dictionary)
        # dispatch task to the worker
        receiver = msg.receiver
        if receiver.is_broadcast:
            self.__broadcast_worker.add_msg(msg=msg)
            res = 'Message broadcasting'
        elif receiver.is_group:
            self.__group_worker.add_msg(msg=msg)
            res = 'Group Message delivering'
        else:
            self.__single_worker.add_msg(msg=msg)
            res = 'Message delivering'
        sender = msg.sender
        if sender.type == NetworkType.STATION:
            # no need to respond receipt to station
            return None
        # # check roaming stations
        # stations = _roaming_stations(user=msg.sender)
        # if self.station not in stations:
        #     # only respond to my own users
        #     return None
        return msg_receipt(msg=msg, text=res)


def _roaming_stations(user: ID) -> List[ID]:
    # check from login command
    cmd = g_database.login_command(identifier=user)
    if cmd is not None:
        station = cmd.station
        if station is not None:
            sid = station.get('ID')
            sid = ID.parse(identifier=sid)
            if sid is not None:
                return [sid]
    # TODO: check from Redis
    #       with key - 'dim.network.{StationID}.online-users'
    #       or key - 'dim.network.{UserID}.login-stations'?
    return []


def _push_message(msg: ReliableMessage, receiver: ID) -> int:
    """ push message to user """
    success = 0
    sessions = g_session_server.active_sessions(identifier=receiver)
    for sess in sessions:
        if sess.push_message(msg=msg):
            success += 1
    return success


def _redirect_message(msg: ReliableMessage, neighbor: ID, bridge: ID) -> int:
    """ redirect message to neighbor station for roaming user """
    cnt = _push_message(msg=msg, receiver=neighbor)
    if cnt == 0:
        Log.warning('remote station (%s) not connected, trying bridge (%s)...' % (neighbor, bridge))
        clone = msg.copy_dictionary()
        clone['target'] = str(neighbor)
        msg = ReliableMessage.parse(msg=clone)
        cnt = _push_message(msg=msg, receiver=bridge)
        if cnt == 0:
            Log.error('station bridge (%s) not connected, cannot redirect.' % bridge)
    return cnt


def _deliver_message(msg: ReliableMessage, receiver: ID, station: ID) -> Optional[Content]:
    # 1. try online sessions
    cnt = _push_message(msg=msg, receiver=receiver)
    # 2. check roaming stations
    neighbors = _roaming_stations(user=receiver)
    for sid in neighbors:
        if sid == station:
            continue
        # 2.1. redirect message to the roaming station
        cnt += _redirect_message(msg=msg, neighbor=sid, bridge=station)
    if cnt > 0:
        return msg_receipt(msg=msg, text='Message delivered to %d session(s)' % cnt)
    # 3. push notification
    res = _push_notification(msg=msg, receiver=receiver)
    return msg_receipt(msg=msg, text=res)


def _push_notification(msg: ReliableMessage, receiver: ID) -> str:
    service = Dispatcher().push_service
    if service is None:
        Log.error('push notification service not initialized')
        return 'Message cached.'
    # fetch sender, group ID & msg type
    sender = msg.sender
    group = msg.group
    msg_type = msg.type
    if msg_type is None:
        msg_type = 0
    elif msg_type == ContentType.FORWARD:
        # check origin message info
        origin = msg.get('origin')
        if isinstance(origin, dict):
            value = ID.parse(identifier=origin.get('sender'))
            if value is not None:
                sender = value
            value = ID.parse(identifier=origin.get('group'))
            if value is not None:
                group = value
            value = origin.get('type')
            if value is not None:
                msg_type = value
            msg.pop('origin')
    # check mute-list
    if g_database.is_muted(sender=sender, receiver=receiver, group=group):
        return 'Message cached.'
    # push notification
    text = build_push_message(sender=sender, receiver=receiver, group=group, msg_type=msg_type, msg=msg)
    if text is None or len(text) == 0:
        Log.warning('ignore msg type: %d' % msg_type)
        return 'Message cached.'
    else:
        Log.info('push notification: %s' % text)
        service.push_notification(sender=sender, receiver=receiver, message=text)
        return 'Message pushed.'


class Worker(threading.Thread, Logging):

    def __init__(self):
        super().__init__()
        self.__running = True
        self.__station: Optional[ID] = None
        self.__neighbors: Set[ID] = set()                # station ID list
        self.__waiting_list: List[ReliableMessage] = []  # ReliableMessage list
        self.__lock = threading.Lock()

    @property
    def station(self) -> ID:
        return self.__station

    @station.setter
    def station(self, server: ID):
        self.__station = server

    @property
    def neighbors(self) -> Set[ID]:
        with self.__lock:
            return self.__neighbors.copy()

    def add_neighbor(self, station: ID):
        assert self.station is not None, 'set station ID first'
        with self.__lock:
            if station != self.station:
                self.__neighbors.add(station)

    def remove_neighbor(self, station: ID):
        with self.__lock:
            self.__neighbors.discard(station)

    def add_msg(self, msg: ReliableMessage):
        with self.__lock:
            self.__waiting_list.append(msg)

    def pop_msg(self) -> Optional[ReliableMessage]:
        with self.__lock:
            if len(self.__waiting_list) > 0:
                return self.__waiting_list.pop(0)

    @abstractmethod
    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        pass

    #
    #   Run Loop
    #
    def run(self):
        self.info('dispatcher starting...')
        while self.__running:
            try:
                while self.__running:
                    msg = self.pop_msg()
                    if msg is None:
                        time.sleep(0.25)
                        break
                    res = self.deliver(msg=msg)
                    if res is not None:
                        # TODO: respond the delivering result to the sender
                        pass
            except Exception as error:
                self.error('dispatcher error: %s' % error)
                traceback.print_exc()
            finally:
                # sleep for next loop
                time.sleep(0.25)
        self.info('dispatcher exit!')

    def stop(self):
        self.__running = False


class SingleDispatcher(Worker):
    """ deliver personal message """

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        return _deliver_message(msg=msg, receiver=msg.receiver, station=self.station)


class GroupDispatcher(Worker):
    """ let the assistant to process this group message """

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        assistants = g_facebook.assistants(identifier=msg.receiver)
        if assistants is None or len(assistants) == 0:
            raise LookupError('failed to get assistant for group: %s' % msg.receiver)
        bot = assistants[0]
        self.info('deliver group message to assistant: %s' % bot)
        return _deliver_message(msg=msg, receiver=bot, station=self.station)


class BroadcastDispatcher(Worker):
    """ broadcast (split and deliver) to everyone """

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        sender = msg.sender
        receiver = msg.receiver
        group = msg.group
        # check for search engine: 'archivist'
        if receiver in ['archivist@anywhere', 'archivists@everywhere']:
            self.info('forward search command to archivist: %s -> %s' % (sender, receiver))
            return self.__deliver_to_archivists(msg=msg)
        # check for group bots: assistants
        if receiver in ['assistant@anywhere', 'assistants@everywhere']:
            self.info('forward group message to assistants: %s -> %s, %s' % (sender, receiver, group))
            return self.__deliver_to_assistants(msg=msg)
        # check for neighbor stations
        if receiver in ['station@anywhere', 'stations@everywhere', str(ANYONE), str(EVERYONE)]:
            self.info('forward message to neighbors: %s -> %s, %s' % (sender, receiver, group))
            return self.__deliver_to_neighbors(msg=msg)
        # TODO: check for other broadcast IDs
        self.warning('failed to deliver message: %s' % msg)

    def __deliver_to_archivists(self, msg: ReliableMessage) -> Optional[Content]:
        archivist = ID.parse(identifier='archivist')
        if archivist is None:
            self.error('failed to get search bot: archivist')
        elif _push_message(msg=msg, receiver=archivist) > 0:
            # response
            text = 'Search command forward to archivist: ' % archivist
            res = TextContent(text=text)
            res.group = msg.group
            return res

    def __deliver_to_assistants(self, msg: ReliableMessage) -> Optional[Content]:
        assistants = g_facebook.assistants(identifier=msg.receiver)
        success = 0
        for ass in assistants:
            cnt = _push_message(msg=msg, receiver=ass)
            if cnt > 0:
                success += 1
            else:
                self.warning('failed to push message to assistant: %s' % ass)
        # response
        text = 'Message broadcast to %d/%d assistants' % (success, len(assistants))
        res = TextContent(text=text)
        res.group = msg.group
        return res

    def __deliver_to_neighbors(self, msg: ReliableMessage) -> Optional[Content]:
        # 0. check neighbor stations
        neighbors = self.neighbors
        candidates = set()
        for sid in neighbors:
            # check station that traced
            if not msg_traced(msg=msg, node=sid):
                candidates.add(sid)
            else:
                sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
                self.info('ignore traced msg [%s]: %s -> %s\n neighbor %s in %s' %
                          (sig, msg.sender, msg.receiver, sid, msg.get('traces')))
        # 1. push to all neighbors connected th current station
        sent_neighbors = []
        success = 0
        for sid in candidates:
            # push to neighbor station
            cnt = _push_message(msg=msg, receiver=sid)
            if cnt > 0:
                sent_neighbors.append(str(sid))
                success += 1
            else:
                sig = get_msg_sig(msg=msg)  # last 6 bytes (signature in base64)
                self.warning('failed to push message (%s) to remote station: %s' % (sig, sid))
        # 2. push to the bridge (octopus) of current station
        sent_neighbors.append(str(self.station))
        msg['sent_neighbors'] = sent_neighbors
        self.info('push to the bridge (%s) ignoring sent stations: %s' % (self.station, sent_neighbors))
        cnt = _push_message(msg=msg, receiver=self.station)
        if cnt == 0:
            # FIXME: what about the failures
            self.error('failed to push message to station bridge: %s' % self.station)
        # response
        text = 'Message broadcast to %d/%d stations' % (success, len(neighbors))
        res = TextContent(text=text)
        res.group = msg.group
        return res
