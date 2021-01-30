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
    DIM Network Monitor
    ~~~~~~~~~~~~~~~~~~~

    Recording DIM network events
"""

import os
import threading
import time
import traceback
from typing import List, Optional

from dimp import ID, NetworkType

from libs.utils.log import current_time
from libs.utils import Singleton, Log, Logging
from libs.utils import Notification, NotificationObserver, NotificationCenter
from libs.common import NotificationNames
from libs.common import Storage
from libs.server import Session


@Singleton
class Monitor(NotificationObserver):

    def __init__(self):
        super().__init__()
        self.__recorder = Recorder()
        # observing notifications
        nc = NotificationCenter()
        nc.add(observer=self, name=NotificationNames.CONNECTED)
        nc.add(observer=self, name=NotificationNames.DISCONNECTED)
        nc.add(observer=self, name=NotificationNames.USER_LOGIN)
        nc.add(observer=self, name=NotificationNames.USER_ONLINE)
        nc.add(observer=self, name=NotificationNames.USER_OFFLINE)
        nc.add(observer=self, name=NotificationNames.DELIVER_MESSAGE)

    def __del__(self):
        self.__recorder.stop()
        self.__recorder = None
        nc = NotificationCenter()
        nc.remove(observer=self, name=NotificationNames.CONNECTED)
        nc.remove(observer=self, name=NotificationNames.DISCONNECTED)
        nc.remove(observer=self, name=NotificationNames.USER_LOGIN)
        nc.remove(observer=self, name=NotificationNames.USER_ONLINE)
        nc.remove(observer=self, name=NotificationNames.USER_OFFLINE)
        nc.remove(observer=self, name=NotificationNames.DELIVER_MESSAGE)

    #
    #    Notification Observer
    #
    def received_notification(self, notification: Notification):
        self.__recorder.append(notification)

    def start(self):
        self.__recorder.start()

    def stop(self):
        self.__recorder.stop()


def save_freshman(identifier: ID) -> bool:
    """ Save freshman ID in a text file for the robot

        file path: '.dim/freshmen.txt'
    """
    path = os.path.join(Storage.root, 'freshmen.txt')
    # check whether ID exists
    text = Storage.read_text(path=path)
    if text is not None:
        array = text.splitlines()
        for item in array:
            if item == identifier:
                # already exists
                return False
    # append as new line
    new_line = str(identifier) + '\n'
    Log.info('Saving freshman: %s' % identifier)
    return Storage.append_text(text=new_line, path=path)


def save_statistics(login_cnt: int, msg_cnt: int, g_msg_cnt: int) -> bool:
    """ Save statistics in a text file for administrators

        file path: '.dim/counter.txt
    """
    path = os.path.join(Storage.root, 'counter.txt')
    now = current_time()
    new_line = '%s\t%d\t%d\t%d\n' % (now, login_cnt, msg_cnt, g_msg_cnt)
    return Storage.append_text(text=new_line, path=path)


class Recorder(threading.Thread, Logging):

    FLUSH_INTERVAL = 3600

    def __init__(self):
        super().__init__()
        self.__running = True
        self.__events: List[Notification] = []
        self.__lock = threading.Lock()
        # statistics
        self.__login_count = 0
        self.__message_count = 0
        self.__group_message_count = 0
        self.__flush_time = time.time() + self.FLUSH_INTERVAL  # next time to save statistics

    def append(self, event: Notification):
        with self.__lock:
            self.__events.append(event)

    def pop(self) -> Optional[Notification]:
        with self.__lock:
            if len(self.__events) > 0:
                return self.__events.pop(0)

    def __save(self):
        now = time.time()
        if now > self.__flush_time:
            # get
            login_cnt = self.__login_count
            msg_cnt = self.__message_count
            g_msg_cnt = self.__group_message_count
            # clear
            self.__login_count = 0
            self.__message_count = 0
            self.__group_message_count = 0
            self.__flush_time = now + self.FLUSH_INTERVAL  # next flush time
            # save
            save_statistics(login_cnt=login_cnt, msg_cnt=msg_cnt, g_msg_cnt=g_msg_cnt)

    def __process(self, event: Notification):
        name = event.name
        info = event.info
        if name == NotificationNames.CONNECTED:
            session = info.get('session')
            assert isinstance(session, Session), 'session error: %s' % session
            client_address = session.client_address
            self.debug('client connected: %s' % str(client_address))
        elif name == NotificationNames.DISCONNECTED:
            session = info.get('session')
            assert isinstance(session, Session), 'session error: %s' % session
            identifier = session.identifier
            client_address = session.client_address
            self.debug('client disconnected: %s, %s' % (client_address, identifier))
        elif name == NotificationNames.USER_LOGIN:
            identifier = ID.parse(identifier=info.get('ID'))
            client_address = info.get('client_address')
            self.debug('user login: %s, %s' % (client_address, identifier))
            # counter
            self.__login_count += 1
            # check for new user to this station
            save_freshman(identifier=identifier)
        elif name == NotificationNames.USER_ONLINE:
            identifier = ID.parse(identifier=info.get('ID'))
            client_address = info.get('client_address')
            station = ID.parse(identifier=info.get('station'))
            if client_address is None:
                self.debug('user roaming: %s -> %s' % (identifier, station))
            else:
                self.debug('user online: %s, %s' % (client_address, identifier))
        elif name == NotificationNames.USER_OFFLINE:
            identifier = ID.parse(identifier=info.get('ID'))
            client_address = info.get('client_address')
            self.debug('user offline: %s, %s' % (client_address, identifier))
        elif name == NotificationNames.DELIVER_MESSAGE:
            sender = ID.parse(identifier=info.get('sender'))
            receiver = ID.parse(identifier=info.get('receiver'))
            if sender.type in [NetworkType.MAIN, NetworkType.BTC_MAIN]:
                if receiver.type in [NetworkType.MAIN, NetworkType.BTC_MAIN]:
                    self.__message_count += 1
                elif receiver.type == NetworkType.GROUP:
                    self.__group_message_count += 1
            self.debug('delivering message: %s -> %s' % (sender, receiver))

    #
    #   Run Loop
    #
    def run(self):
        event = None
        while self.__running:
            try:
                # process events
                event = self.pop()
                while event is not None:
                    self.__process(event=event)
                    event = self.pop()
                # save statistics
                self.__save()
            except Exception as error:
                self.error('failed to process: %s, %s' % (event, error))
                traceback.print_exc()
            finally:
                self.debug('nothing to do, sleeping')
                time.sleep(0.5)

    def stop(self):
        self.__running = False
