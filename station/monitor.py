#! /usr/bin/env python3
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

import threading
import time
import traceback
from typing import Optional

from dimp import ID, NetworkType
from startrek.fsm import Runner

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils.log import current_time
from libs.utils import Log, Logging
from libs.database import Storage, Database
from libs.common import NotificationNames

from station.config import MonitorArrow


#
#   Process
#


def save_statistics(login_cnt: int, msg_cnt: int, g_msg_cnt: int) -> bool:
    """ Save statistics in a text file for administrators

        file path: '.dim/counter.txt
    """
    path = os.path.join(Storage.root, 'counter.txt')
    now = current_time()
    new_line = '%s\t%d\t%d\t%d\n' % (now, login_cnt, msg_cnt, g_msg_cnt)
    return Storage.append_text(text=new_line, path=path)


class Recorder(Runner, Logging):

    FLUSH_INTERVAL = 3600

    def __init__(self):
        super().__init__()
        self.__events = []
        self.__lock = threading.Lock()
        # statistics
        self.__login_count = 0
        self.__message_count = 0
        self.__group_message_count = 0
        self.__flush_time = time.time() + self.FLUSH_INTERVAL  # next time to save statistics

    def append(self, event: dict):
        with self.__lock:
            self.__events.append(event)

    def shift(self) -> Optional[dict]:
        with self.__lock:
            if len(self.__events) > 0:
                return self.__events.pop(0)

    def __save(self) -> bool:
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
            return save_statistics(login_cnt=login_cnt, msg_cnt=msg_cnt, g_msg_cnt=g_msg_cnt)

    def __process(self, event: dict):
        name = event.get('name')
        info = event.get('info')
        if name == NotificationNames.USER_LOGIN:
            identifier = ID.parse(identifier=info.get('ID'))
            client_address = info.get('client_address')
            station = ID.parse(identifier=info.get('station'))
            login_time = info.get('time')
            self.debug('user login: %s, %s' % (client_address, identifier))
            # counter
            self.__login_count += 1
            # update online users
            if identifier is None or station is None:
                self.error('user/station empty: %s' % info)
            else:
                db = Database()
                db.add_online_user(station=station, user=identifier, login_time=login_time)
        elif name == NotificationNames.USER_ONLINE:
            identifier = ID.parse(identifier=info.get('ID'))
            client_address = info.get('client_address')
            station = ID.parse(identifier=info.get('station'))
            login_time = info.get('time')
            if client_address is None:
                self.debug('user roaming: %s -> %s' % (identifier, station))
            else:
                self.debug('user online: %s, %s -> %s' % (identifier, client_address, station))
            # update online users
            if identifier is None or station is None:
                self.error('user/station empty: %s' % info)
            else:
                db = Database()
                db.add_online_user(station=station, user=identifier, login_time=login_time)
        elif name == NotificationNames.USER_OFFLINE:
            identifier = ID.parse(identifier=info.get('ID'))
            client_address = info.get('client_address')
            station = ID.parse(identifier=info.get('station'))
            self.debug('user offline: %s, %s' % (client_address, identifier))
            # update online users
            if identifier is None or station is None:
                self.error('user/station empty: %s' % info)
            else:
                db = Database()
                db.remove_offline_users(station=station, users=[identifier])
        elif name == NotificationNames.DELIVER_MESSAGE:
            sender = ID.parse(identifier=info.get('sender'))
            receiver = ID.parse(identifier=info.get('receiver'))
            if sender.type in [NetworkType.MAIN, NetworkType.BTC_MAIN]:
                if receiver.type in [NetworkType.MAIN, NetworkType.BTC_MAIN]:
                    self.__message_count += 1
                elif receiver.type == NetworkType.GROUP:
                    self.__group_message_count += 1
            self.debug('delivering message: %s -> %s' % (sender, receiver))

    # Override
    def process(self) -> bool:
        event = None
        try:
            event = self.shift()
            if event is None:
                # save statistics
                self.__save()
                return False
            else:
                self.__process(event=event)
                return True
        except Exception as error:
            self.error('failed to process: %s, %s' % (event, error))
            traceback.print_exc()
        finally:
            time.sleep(0.5)


class Worker(Runner, Logging):

    def __init__(self, recorder: Recorder):
        super().__init__()
        self.__arrow = MonitorArrow.aim()
        self.__recorder = recorder

    # Override
    def process(self) -> bool:
        event = None
        try:
            # get next event
            event = self.__arrow.receive()
            if event is None:
                # nothing to do now, return False to have a rest
                return False
            # let recorder to do the job
            self.__recorder.append(event=event)
            return True
        except Exception as error:
            self.error('failed to parse: %s, error: %s' % (event, error))


if __name__ == '__main__':
    Log.info(msg='>>> starting monitor ...')
    g_recorder = Recorder()
    g_monitor = Worker(recorder=g_recorder)
    # start as thread
    g_recorder_t = threading.Thread(target=g_recorder.run)
    g_recorder_t.start()
    g_monitor.run()
    g_recorder.stop()
    Log.info(msg='>>> monitor exits.')
