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
from threading import Thread
from typing import Optional, Union, List

from dimp import ID
from dimp import ReliableMessage
from dimp import ContentType, Content, TextContent
from dimsdk import Station
from dimsdk import ReceiptCommand

from libs.utils import Log
from libs.common import Server
from libs.common import Database
from libs.common.push_message_service import PushMessageService

from .session import Session, SessionServer
from .facebook import ServerFacebook


class Dispatcher(Thread):

    def __init__(self):
        super().__init__()
        self.station: Server = None
        self.session_server: SessionServer = None
        # self.apns: ApplePushNotificationService = None
        self.push_service: PushMessageService = PushMessageService()
        self.__neighbors: List[ID] = []     # ID list
        self.__waiting_list: List[ReliableMessage] = []  # ReliableMessage list
        self.__waiting_list_lock = threading.Lock()

    def info(self, msg: str):
        Log.info('%s > %s >\t%s' % (threading.current_thread().getName(), self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

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
        if station == self.station.identifier:
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

    def __traced(self, msg: ReliableMessage, station: Station) -> bool:
        sid = station.identifier
        traces = msg.get('traces')
        if traces is None:
            # broadcast message starts from here
            traces = [sid]
        else:
            for node in traces:
                if isinstance(node, str):
                    if sid == node:
                        return True
                elif isinstance(node, dict):
                    if sid == node.get('ID'):
                        return True
                else:
                    self.error('traces node error: %s' % node)
            # broadcast message go through here
            traces.append(sid)
        msg['traces'] = ID.revert(members=traces)
        return False

    def __broadcast_message(self, msg: ReliableMessage) -> Optional[Content]:
        """ Deliver message to everyone@everywhere, including all neighbours """
        self.info('broadcasting message %s' % msg)
        if self.__traced(msg=msg, station=self.station):
            self.error('ignore traced msg: %s in %s' % (self.station, msg.get('traces')))
            return None
        # push to all neighbors connected th current station
        neighbors = self.__neighbors.copy()
        sent_neighbors = []
        success = 0
        for sid in neighbors:
            if sid == self.station.identifier:
                continue
            sessions = self.__online_sessions(receiver=sid)
            if sessions is None:
                self.info('remote station (%s) not connected, try later.' % sid)
                continue
            if self.__push_message(msg=msg, receiver=sid, sessions=sessions):
                sent_neighbors.append(sid)
                success += 1
        # push to the bridge (octopus) of current station
        sid = self.station.identifier
        sessions = self.__online_sessions(receiver=sid)
        if sessions is not None:
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

    def __push_message(self, msg: ReliableMessage, receiver: ID, sessions: List[Session]) -> bool:
        self.info('%s is online(%d), try to push message for: %s' % (receiver, len(sessions), msg.sender))
        success = 0
        session_server = self.session_server
        for sess in sessions:
            if sess.valid is False or sess.active is False:
                # self.info('session invalid %s' % sess)
                continue
            request_handler = session_server.get_handler(client_address=sess.client_address)
            if request_handler is None:
                self.error('handler lost: %s' % sess)
                continue
            if request_handler.push_message(msg):
                success = success + 1
            else:
                self.error('failed to push message via connection (%s, %s)' % sess.client_address)
        if success > 0:
            self.info('message for user %s pushed to %d sessions' % (receiver, success))
            return True

    def __redirect_message(self, msg: ReliableMessage, receiver: ID, neighbor: ID) -> bool:
        self.info('%s is roaming, try to redirect: %s' % (receiver, neighbor))
        sessions = self.__online_sessions(receiver=neighbor)
        if sessions is None:
            self.info('remote station (%s) not connected, trying bridge...' % neighbor)
            neighbor = self.station.identifier
            sessions = self.__online_sessions(receiver=neighbor)
            if sessions is None:
                self.error('station bridge (%s) not connected, cannot redirect.' % neighbor)
                return False
        if self.__push_message(msg=msg, receiver=neighbor, sessions=sessions):
            self.info('message for user %s redirected to %s' % (receiver, neighbor))
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
        if (now - login.time) > (3600 * 24 * 7):
            t_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(login.time))
            self.info('%s login expired: [%s] %s' % (receiver, t_str, login))
            return None
        sid = ID.parse(identifier=station.get('ID'))
        if sid == self.station.identifier:
            return None
        return sid

    def __online_sessions(self, receiver: ID) -> Optional[List[Session]]:
        sessions = self.session_server.all(identifier=receiver)
        if sessions is not None and len(sessions) == 0:
            sessions = None
        return sessions

    def __push_notification(self, sender: ID, receiver: ID, group: ID, msg_type: int=0) -> bool:
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
            self.info('ignore msg type: %d' % msg_type)
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
        return self.push_service.push(sender, receiver, text)

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
        sessions = self.__online_sessions(receiver=receiver)
        if sessions is None:
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

        self.info('%s is offline, store message from: %s' % (receiver, sender))
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
        while self.station.running:
            # noinspection PyBroadException
            try:
                self.__run_unsafe()
            except Exception as error:
                self.error('dispatcher error: %s' % error)
            finally:
                # sleep for next loop
                time.sleep(0.1)
        self.info('dispatcher exit!')
