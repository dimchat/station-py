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

from dimp import ID, NetworkType
from dimsdk import Station

from libs.utils import Singleton, Logging
from libs.utils import Notification, NotificationObserver, NotificationCenter
from libs.common import NotificationNames
from libs.common import Database
from libs.server import SessionServer
from libs.server import ServerFacebook
from libs.server import Dispatcher


g_facebook = ServerFacebook()
g_database = Database()
g_session_server = SessionServer()
g_dispatcher = Dispatcher()


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

    def get_guests(self) -> List[ID]:
        with self.__lock:
            guests = self.__guests.copy()
            self.__guests.clear()
            return guests

    def add_guest(self, identifier: ID):
        with self.__lock:
            self.__guests.append(identifier)

    def remove_guest(self, identifier: ID):
        with self.__lock:
            self.__guests.remove(identifier)

    def get_roamers(self) -> List[ID]:
        with self.__lock:
            roamers = self.__roamers.copy()
            self.__roamers.clear()
            return roamers

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
        elif name == NotificationNames.USER_LOGIN:
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
    #  Process guests/roamers
    #

    def __process_users(self, users: List[ID]):
        for identifier in users:
            # 1. get cached messages
            self.debug('scanning messages for: %s' % identifier)
            messages = g_database.fetch_all_messages(receiver=identifier)
            # 2. sent messages one by one
            self.info('loaded %d message(s) for: %s' % (len(messages), identifier))
            for msg in messages:
                g_dispatcher.deliver(msg=msg)

    #
    #   Run Loop
    #
    def __run_unsafe(self):
        # process guests
        try:
            self.__process_users(users=self.get_guests())
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
            self.__process_users(users=self.get_roamers())
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
