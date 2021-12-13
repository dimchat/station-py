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
from typing import Optional, Set

from dimp import ID, NetworkType
from dimsdk import Station

from libs.utils import Log, Logging
from libs.utils import Singleton
from libs.utils import Notification, NotificationObserver, NotificationCenter
from libs.common import NotificationNames

from etc.cfg_init import g_database
from station.config import g_dispatcher, g_facebook, g_station


@Singleton
class Receptionist(NotificationObserver, Logging):

    def __init__(self):
        super().__init__()
        self.__running = True
        self.__lock = threading.Lock()
        # current station and guests
        self.__station: Optional[ID] = None
        self.__roamers = set()
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)
        nc.add(observer=self, name=NotificationNames.USER_ROAMING)

    def __del__(self):
        nc = NotificationCenter()
        nc.remove(observer=self, name=NotificationNames.USER_ONLINE)
        nc.remove(observer=self, name=NotificationNames.USER_ROAMING)

    @property
    def station(self) -> ID:
        return self.__station

    @station.setter
    def station(self, server: ID):
        if isinstance(server, Station):
            server = server.identifier
        self.__station = server

    def get_roamers(self) -> Set[ID]:
        with self.__lock:
            roamers = self.__roamers.copy()
            self.__roamers.clear()
            return roamers

    def add_roamer(self, identifier: ID):
        with self.__lock:
            self.__roamers.add(identifier)

    #
    #    Notification Observer
    #
    def received_notification(self, notification: Notification):
        name = notification.name
        info = notification.info
        user = ID.parse(identifier=info.get('ID'))
        if user is None or user.type == NetworkType.STATION:
            self.error('ignore notification: %s' % info)
        elif name == NotificationNames.USER_ONLINE:
            # sid = info.get('station')
            # if sid is not None and sid != self.station:
            self.add_roamer(identifier=user)
        elif name == NotificationNames.USER_ROAMING:
            # add the new roamer for checking cached messages
            self.add_roamer(identifier=user)

    #
    #  Process roamers
    #

    def __process_users(self, users: Set[ID]):
        for identifier in users:
            # 1. get cached messages
            messages = g_database.messages(receiver=identifier)
            self.info('%d message(s) loaded for: %s' % (len(messages), identifier))
            # 2. sent messages one by one
            for msg in messages:
                g_dispatcher.deliver(msg=msg)

    #
    #   Run Loop
    #
    def __run_unsafe(self):
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
            time.sleep(0.25)

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
                time.sleep(0.25)
        self.info('receptionist exit!')

    def stop(self):
        self.__running = False


if __name__ == '__main__':
    Log.info(msg='>>> starting receptionist ...')
    g_facebook.current_user = g_station
    g_worker = Receptionist()
    g_worker.run()
    Log.info(msg='>>> receptionist exists.')
