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

import os
import time
import traceback
from json import JSONDecodeError
from threading import Thread
from typing import Optional, List, Union

from dimp import ID, NetworkType, ReliableMessage
from dimsdk import Station

from libs.utils import Log, Singleton
from libs.utils import Notification, NotificationObserver, NotificationCenter
from libs.common import NotificationNames
from libs.common import Storage, Database
from libs.server import SessionServer
from libs.server import ServerFacebook


g_facebook = ServerFacebook()
g_database = Database()
g_session_server = SessionServer()


def save_freshman(identifier: ID) -> bool:
    """ Save freshman ID in a text file for the robot

        file path: '.dim/freshmen.txt'
    """
    path = os.path.join(Storage.root, 'freshmen.txt')
    # check
    text = Storage.read_text(path=path)
    if text is None:
        lines = []
    else:
        lines = text.splitlines()
    for item in lines:
        if item == identifier:
            # already exists
            return False
    # append
    line = str(identifier) + '\n'
    Log.info('Saving freshman: %s' % identifier)
    return Storage.append_text(text=line, path=path)


@Singleton
class Receptionist(Thread, NotificationObserver):

    def __init__(self):
        super().__init__()
        self.__running = True
        # current station and guests
        self.__station: Optional[ID] = None
        self.__guests = []
        self.__roamers = []
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)

    def __del__(self):
        nc = NotificationCenter()
        nc.remove(observer=self, name=NotificationNames.USER_LOGIN)
        nc.remove(observer=self, name=NotificationNames.USER_ONLINE)

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

    #
    #    Notification Observer
    #
    def received_notification(self, notification: Notification):
        name = notification.name
        info = notification.info
        if name == NotificationNames.USER_LOGIN:
            user = info.get('ID')
            # add the new guest for checking offline messages
            self.add_guest(identifier=user)
        elif name == NotificationNames.USER_ONLINE:
            user = info.get('ID')
            sid = info.get('station')
            if sid is None or sid == self.station:
                # add the new guest for checking offline messages
                self.add_guest(identifier=user)
            else:
                self.add_roamer(identifier=user)

    def add_guest(self, identifier: ID):
        # FIXME: thread safe
        self.__guests.append(identifier)
        # check freshman
        save_freshman(identifier=identifier)

    def remove_guest(self, identifier: ID):
        # FIXME: thread safe
        self.__guests.remove(identifier)

    def add_roamer(self, identifier: ID):
        # FIXME: thread safe
        self.__roamers.append(identifier)

    def remove_roamer(self, identifier: ID):
        # FIXME: thread safe
        self.__roamers.remove(identifier)

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

    def __process_guests(self, guests: List[ID]):
        for identifier in guests:
            if identifier is None:
                # FIXME: while empty ID added?
                continue
            # 1. scan offline messages
            self.debug('%s is connected, scanning messages for it' % identifier)
            batch = g_database.load_message_batch(identifier)
            if batch is None:
                self.debug('no message for this guest, remove it: %s' % identifier)
                self.remove_guest(identifier)
                # post notification: INBOX_EMPTY
                NotificationCenter().post(name=NotificationNames.INBOX_EMPTY, sender=self, info={
                    'ID': identifier,
                })
                continue
            messages = batch.get('messages')
            if messages is None or len(messages) == 0:
                self.error('message batch error: %s' % batch)
                # raise AssertionError('message batch error: %s' % batch)
                continue
            self.debug('got %d message(s) for %s' % (len(messages), identifier))
            # 2. push offline messages one by one
            count = 0
            for msg in messages:
                success = self.__push_message(msg=msg, receiver=identifier)
                if success > 0:
                    # push message success (at least one)
                    count = count + 1
                else:
                    # push message failed, remove session here?
                    break
            # 3. remove messages after success
            total_count = len(messages)
            self.debug('a batch message(%d/%d) pushed to %s' % (count, total_count, identifier))
            g_database.remove_message_batch(batch, removed_count=count)
            if count < total_count:
                # remove the guest on failed
                self.error('pushing message failed(%d/%d) for: %s' % (count, total_count, identifier))
                self.remove_guest(identifier)

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
        # try to redirect message to this station
        sid = station.identifier
        self.debug('checking session for station %s' % sid)
        # get all sessions of the receiver
        sessions = g_session_server.active_sessions(identifier=sid)
        if len(sessions) == 0:
            self.debug('session not found for guest: %s' % sid)
            return 0
        # push this message to all sessions one by one
        success = 0
        for sess in sessions:
            if sess.push_message(msg):
                success = success + 1
            else:
                self.error('failed to push message (%s, %s)' % sess.client_address)
        return success

    def __process_roamers(self, roamers: List[ID]):
        for identifier in roamers:
            # 1. scan offline messages
            self.debug('%s is roaming, scanning messages for it' % identifier)
            batch = g_database.load_message_batch(identifier)
            if batch is None:
                self.debug('no message for this roamer, remove it: %s' % identifier)
                self.remove_roamer(identifier)
                continue
            messages = batch.get('messages')
            if messages is None or len(messages) == 0:
                self.error('message batch error: %s' % batch)
                # raise AssertionError('message batch error: %s' % batch)
                continue
            self.debug('got %d message(s) for %s' % (len(messages), identifier))
            # 2. redirect offline messages one by one
            count = 0
            for msg in messages:
                success = self.__redirect_message(msg=msg, receiver=identifier)
                if success > 0:
                    # redirect message success (at least one)
                    count = count + 1
                else:
                    # redirect message failed, remove session here?
                    break
            # 3. remove messages after success
            total_count = len(messages)
            self.debug('a batch message(%d/%d) redirect for %s' % (count, total_count, identifier))
            g_database.remove_message_batch(batch, removed_count=count)
            if count < total_count:
                # remove the roamer on failed
                self.error('redirect message failed(%d/%d) for: %s' % (count, total_count, identifier))
                self.remove_roamer(identifier)

    #
    #   Run Loop
    #
    def __run_unsafe(self):
        # process guests
        try:
            self.__process_guests(guests=self.__guests.copy())
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
            self.__process_roamers(roamers=self.__roamers.copy())
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
