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
from typing import Optional, Union, List, Set

from dimp import ID, NetworkType, Entity
from dimp import ReliableMessage
from dimp import ContentType, Content, TextContent
from dimsdk import Station

from ..utils import Singleton, Log, Logging
from ..utils import Notification, NotificationObserver, NotificationCenter
from ..push import PushNotificationService
from ..common import NotificationNames
from ..common import Database, SharedFacebook
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
    def push_service(self) -> Optional[PushNotificationService]:
        if self.__push_service is not None:
            return self.__push_service()

    @push_service.setter
    def push_service(self, service: PushNotificationService):
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
        sid = _entity_id(server)
        self.__single_worker.station = sid
        self.__group_worker.station = sid
        self.__broadcast_worker.station = sid

    def add_neighbor(self, station: ID):
        sid = _entity_id(station)
        self.__single_worker.add_neighbor(station=sid)
        self.__group_worker.add_neighbor(station=sid)
        self.__broadcast_worker.add_neighbor(station=sid)

    def remove_neighbor(self, station: Union[Station, ID]):
        sid = _entity_id(station)
        self.__single_worker.remove_neighbor(station=sid)
        self.__group_worker.remove_neighbor(station=sid)
        self.__broadcast_worker.remove_neighbor(station=sid)

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        # post notification for monitor
        NotificationCenter().post(name=NotificationNames.DELIVER_MESSAGE, sender=self, info=msg.dictionary)
        # dispatch task to the worker
        receiver = msg.receiver
        if receiver.is_broadcast:
            self.__broadcast_worker.add_msg(msg=msg)
            res = msg_receipt(msg=msg, text='Message broadcasting')
        elif receiver.is_group:
            self.__group_worker.add_msg(msg=msg)
            res = msg_receipt(msg=msg, text='Group Message delivering')
        else:
            self.__single_worker.add_msg(msg=msg)
            res = msg_receipt(msg=msg, text='Message delivering')
        # only respond to my own users
        stations = _roaming_stations(user=msg.sender)
        if self.station in stations:
            return res


def _entity_id(entity: Union[Entity, ID]) -> ID:
    """ get entity ID """
    if isinstance(entity, Entity):
        return entity.identifier
    elif isinstance(entity, ID):
        return entity
    raise TypeError('failed to get ID: %s' % entity)


def _roaming_stations(user: ID) -> List[ID]:
    stations = []
    cmd = g_database.login_command(identifier=user)
    if cmd is not None:
        station = cmd.station
        last_time = cmd.time
        if isinstance(station, dict) and isinstance(last_time, int):
            # check time expires
            if (time.time() - last_time) < (3600 * 24 * 7):
                sid = ID.parse(identifier=station.get('ID'))
                if sid is not None:
                    stations.append(sid)
    return stations


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
        msg['target'] = str(neighbor)
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
    # 3. store in local cache file
    g_database.store_message(msg)
    # check mute-list
    sender = msg.sender
    group = msg.group
    if not g_database.is_muted(sender=sender, receiver=receiver, group=group):
        # push notification
        msg_type = msg.type
        if msg_type is None:
            msg_type = 0
        elif msg_type == ContentType.FORWARD:
            # check origin message info
            origin = msg.get('origin')
            if isinstance(origin, dict):
                value = origin.get('sender')
                if value is not None:
                    sender = value
                value = origin.get('group')
                if value is not None:
                    group = value
                value = origin.get('type')
                if value is not None:
                    msg_type = value
                msg.pop('origin')
        _push_notification(sender=sender, receiver=receiver, group=group, msg_type=msg_type)
    return msg_receipt(msg=msg, text='Message cached')


def _push_notification(sender: ID, receiver: ID, group: ID, msg_type: int = 0) -> bool:
    """ push notification service """
    service = Dispatcher().push_service
    if service is None:
        Log.error('push notification service not initialized')
        return False
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
    elif msg_type in [ContentType.MONEY, ContentType.TRANSFER]:
        something = 'some money'
    else:
        Log.warning('ignore msg type: %d' % msg_type)
        return False
    from_name = g_facebook.name(identifier=sender)
    to_name = g_facebook.name(identifier=receiver)
    text = 'Dear %s: %s sent you %s' % (to_name, from_name, something)
    if group is not None:
        # group message
        text += ' in group [%s]' % g_facebook.name(identifier=group)
    print('push notification: %s' % text)
    return service.push_notification(sender=sender, receiver=receiver, message=text)


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
        if isinstance(server, Station):
            server = server.identifier
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
                        time.sleep(0.1)
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
                time.sleep(0.1)
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
        return _deliver_message(msg=msg, receiver=assistants[0], station=self.station)


class BroadcastDispatcher(Worker):
    """ broadcast (split and deliver) to everyone """

    def deliver(self, msg: ReliableMessage) -> Optional[Content]:
        # FIXME: now only broadcast message to all stations
        #        what about robots?
        self.debug('broadcasting message from: %s' % msg.sender)
        # 1. push to all neighbors connected th current station
        neighbors = self.neighbors
        sent_neighbors = []
        success = 0
        for sid in neighbors:
            # check traces
            if msg_traced(msg=msg, node=sid):  # and is_broadcast_message(msg=msg):
                self.info('ignore traced msg: %s in %s' % (sid, msg.get('traces')))
                continue
            assert sid != self.station, 'neighbors error: %s, %s' % (self.station, neighbors)
            # push to neighbor station
            cnt = _push_message(msg=msg, receiver=sid)
            if cnt > 0:
                sent_neighbors.append(str(sid))
                success += 1
            else:
                self.warning('failed to push message to remote station: %s' % sid)
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
