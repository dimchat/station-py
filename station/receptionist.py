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
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""

import threading
import time
import traceback
from json import JSONDecodeError
from typing import Optional, List, Union

from dimp import ID, NetworkType, ReliableMessage
from dimsdk import Station

from libs.utils import Singleton, Logging
from libs.utils import Notification, NotificationObserver, NotificationCenter
from libs.common import NotificationNames
from libs.common import Database
from libs.server import SessionServer
from libs.server import ServerFacebook


g_facebook = ServerFacebook()
g_database = Database()
g_session_server = SessionServer()


@Singleton
class Receptionist(threading.Thread, NotificationObserver, Logging):

    def __init__(self):
        super().__init__()
        self.__running = True
        self.__lock = threading.Lock()
        # current station and guests
        self.__station: Optional[ID] = None
        self.__guests = []
        self.__roamers = []
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)
        nc.add(observer=self, name=NotificationNames.USER_ROAMING)

    def __del__(self):
        nc = NotificationCenter()
        nc.remove(observer=self, name=NotificationNames.USER_LOGIN)
        nc.remove(observer=self, name=NotificationNames.USER_ONLINE)
        nc.remove(observer=self, name=NotificationNames.USER_ROAMING)

    @property
    def station(self) -> ID:
        return self.__station

    @station.setter
    def station(self, server: Union[ID, Station]):
        if isinstance(server, Station):
            server = server.identifier
        self.__station = server

    @property
    def guests(self) -> List[ID]:
        with self.__lock:
            return self.__guests.copy()

    def add_guest(self, identifier: ID):
        with self.__lock:
            self.__guests.append(identifier)

    def remove_guest(self, identifier: ID):
        with self.__lock:
            self.__guests.remove(identifier)

    @property
    def roamers(self) -> List[ID]:
        with self.__lock:
            return self.__roamers.copy()

    def add_roamer(self, identifier: ID):
        with self.__lock:
            self.__roamers.append(identifier)

    def remove_roamer(self, identifier: ID):
        with self.__lock:
            self.__roamers.remove(identifier)

    #
    #    Notification Observer
    #
    def received_notification(self, notification: Notification):
        name = notification.name
        info = notification.info
        user = ID.parse(identifier=info.get('ID'))
        if user is None or user.type == NetworkType.STATION:
            self.error('ignore notification: %s' % info)
            return
        if name == NotificationNames.USER_LOGIN:
            # add the new guest for checking offline messages
            self.add_guest(identifier=user)
        elif name == NotificationNames.USER_ONLINE:
            sid = info.get('station')
            if sid is None or sid == self.station:
                # add the new guest for checking offline messages
                self.add_guest(identifier=user)
            else:
                # add the new roamer for checking cached messages
                self.add_roamer(identifier=user)
        elif name == NotificationNames.USER_ROAMING:
            # add the new roamer for checking cached messages
            self.add_roamer(identifier=user)

    #
    #   Guests login this station
    #

    def __push_message(self, msg: ReliableMessage, receiver: ID) -> int:
        # get all sessions of the receiver
        self.debug('checking session for new guest %s' % receiver)
        sessions = g_session_server.active_sessions(identifier=receiver)
        if len(sessions) == 0:
            self.warning('session not found for guest: %s' % receiver)
            return 0
        # push this message to all sessions one by one
        success = 0
        for sess in sessions:
            if sess.push_message(msg):
                success = success + 1
            else:
                self.error('failed to push message (%s, %s)' % sess.client_address)
        return success

    #
    #   Roamers login another station
    #

    def __login_station(self, identifier: ID) -> Optional[Station]:
        login = g_database.login_command(identifier=identifier)
        if login is None:
            self.error('login info not found: %s' % identifier)
            return None
        station = login.station
        if station is None:
            self.error('login station not found: %s -> %s' % (identifier, login))
            return None
        sid = station.get('ID')
        if sid is None:
            self.error('login station error: %s -> %s' % (identifier, login))
            return None
        sid = ID.parse(identifier=sid)
        assert sid.type == NetworkType.STATION, 'station ID error: %s' % station
        if sid == self.station:
            self.debug('login station is current station: %s -> %s' % (identifier, sid))
            return None
        # anything else?
        return g_facebook.user(identifier=sid)

    def __redirect_message(self, msg: ReliableMessage, receiver: ID) -> int:
        # get station of the roamer
        self.debug('checking station for new roamer %s' % receiver)
        station = self.__login_station(identifier=receiver)
        if station is None:
            self.debug('station not found for roamer: %s' % receiver)
            return 0
        station = station.identifier
        if station == self.station:
            self.error('user not roaming: %s -> %s' % (receiver, station))
            return 0
        # try to redirect message to the roaming station
        self.debug('checking session for station %s' % station)
        # get all sessions of the receiver
        sessions = g_session_server.active_sessions(identifier=station)
        if len(sessions) == 0:
            self.debug('session not found for station: %s, try bridge' % station)
            sessions = g_session_server.active_sessions(identifier=self.station)
            if len(sessions) == 0:
                self.warning('bridge not built: %s' % self.station)
                return 0
        # push this message to all sessions one by one
        success = 0
        for sess in sessions:
            if sess.push_message(msg):
                success = success + 1
            else:
                self.error('failed to push message (%s, %s)' % sess.client_address)
        return success

    #
    #  Process guests/roamers
    #

    def __process_users(self, users: List[ID], is_roaming: bool):
        # load cached messages
        cached_messages = {}
        for identifier in users:
            messages = g_database.fetch_all_messages(receiver=identifier)
            if len(messages) == 0:
                continue
            self.info('loaded %d message(s) for: %s' % (len(messages), identifier))
            cached_messages[identifier] = messages
        # process all cached messages for these users
        while len(users) > 0:
            current_users = users.copy()
            for identifier in current_users:
                if identifier is None:
                    # FIXME: why empty ID added?
                    continue
                # 1. get cached messages
                self.debug('scanning messages for: %s' % identifier)
                messages = cached_messages.get(identifier)
                if messages is None or len(messages) == 0:
                    self.debug('no message for %s, remove it' % identifier)
                    users.remove(identifier)
                    if is_roaming:
                        self.remove_roamer(identifier=identifier)
                    else:
                        self.remove_guest(identifier=identifier)
                    # post notification: INBOX_EMPTY
                    NotificationCenter().post(name=NotificationNames.INBOX_EMPTY, sender=self, info={
                        'ID': identifier,
                    })
                    continue
                msg_cnt = len(messages)
                self.debug('got %d message(s) for %s' % (msg_cnt, identifier))
                # 2. sent messages one by one
                msg = messages.pop(0)
                if is_roaming:
                    success = self.__redirect_message(msg=msg, receiver=identifier)
                else:
                    success = self.__push_message(msg=msg, receiver=identifier)
                if success > 0:
                    self.info('message forwarded to %d session(s) for: %s' % (success, identifier))
                    continue
                self.error('failed to forward message, store %d left for: %s' % (msg_cnt, identifier))
                # 3. store message left
                g_database.store_message(msg=msg)
                for msg in messages:
                    g_database.store_message(msg=msg)
                # 4. remove
                users.remove(identifier)
                if is_roaming:
                    self.remove_roamer(identifier=identifier)
                else:
                    self.remove_guest(identifier=identifier)

    #
    #   Run Loop
    #
    def __run_unsafe(self):
        # process guests
        try:
            self.__process_users(users=self.guests, is_roaming=False)
        except IOError as error:
            self.error('IO error %s' % error)
        except JSONDecodeError as error:
            self.error('JSON decode error %s' % error)
        except TypeError as error:
            self.error('type error %s' % error)
            traceback.print_exc()
        except ValueError as error:
            self.error('value error %s' % error)
        finally:
            # sleep for next loop
            time.sleep(0.1)
        # process roamers
        try:
            self.__process_users(users=self.roamers, is_roaming=True)
        except IOError as error:
            self.error('IO error %s' % error)
        except JSONDecodeError as error:
            self.error('JSON decode error %s' % error)
        except TypeError as error:
            self.error('type error %s' % error)
        except ValueError as error:
            self.error('value error %s' % error)
        finally:
            # sleep for next loop
            time.sleep(0.1)

    def run(self):
        self.info('receptionist starting...')
        while self.__running:
            # noinspection PyBroadException
            try:
                self.__run_unsafe()
            except Exception as error:
                self.error('receptionist error: %s' % error)
                traceback.print_exc()
            finally:
                # sleep for next loop
                time.sleep(0.1)
        self.info('receptionist exit!')

    def stop(self):
        self.__running = False
