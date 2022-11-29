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
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""

import threading
import time
import traceback
from typing import Union, Set, Dict

from dimp import ID, ReliableMessage

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils.log import Log, Logging
from libs.utils.ipc import ReceptionistPipe
from libs.utils import Runner
from libs.common import NotificationNames

from etc.cfg_init import g_database


class Receptionist(Runner, Logging):

    DELAY = 5  # seconds

    def __init__(self):
        super().__init__()
        # waiting queue for offline messages
        self.__guests: Set[ID] = set()
        self.__times: Dict[ID, float] = {}
        self.__lock = threading.Lock()
        self.__pipe = ReceptionistPipe.secondary()

    def get_guests(self) -> Set[ID]:
        with self.__lock:
            guests = set()
            now = time.time()
            for g in self.__guests:
                t = self.__times.get(g)
                if t is None or t < now:
                    guests.add(g)
            for g in guests:
                self.__times.pop(g, None)
                self.__guests.discard(g)
            return guests

    def add_guest(self, identifier: ID):
        with self.__lock:
            self.__guests.add(identifier)
            self.__times[identifier] = time.time() + self.DELAY

    def send(self, msg: Union[dict, ReliableMessage]) -> int:
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        return self.__pipe.send(obj=msg)

    def start(self):
        self.__pipe.start()
        self.run()

    # Override
    def stop(self):
        self.__pipe.stop()
        super().stop()

    # Override
    def process(self) -> bool:
        event = None
        try:
            event = self.__pipe.receive()
            if isinstance(event, dict):
                name = event.get('name')
                info = event.get('info')
                assert name is not None and info is not None, 'event error: %s' % event
                self.__process_notification(name=name, info=info)
                return True
            else:
                self.__process_users(users=self.get_guests())
        except Exception as error:
            self.error('event error: %s, %s' % (event, error))
            traceback.print_exc()

    def __process_notification(self, name: str, info: dict):
        self.debug(msg='received event: %s' % name)
        identifier = ID.parse(identifier=info.get('ID'))
        assert identifier is not None, 'ID error: %s, %s' % (name, info)
        client_address = info.get('client_address')
        if name == NotificationNames.USER_LOGIN:
            assert client_address is not None, 'client address error: %s, %s' % (name, info)
            self.add_guest(identifier=identifier)
            return True
        if name == NotificationNames.USER_ONLINE:
            if client_address is None:
                self.add_guest(identifier=identifier)
                return True
        self.warning(msg='unknown event: %s' % name)

    def __process_users(self, users: Set[ID]):
        for identifier in users:
            # 1. get cached messages
            messages = g_database.messages(receiver=identifier)
            self.info('%d message(s) loaded for: %s' % (len(messages), identifier))
            # 2. sent messages one by one
            for msg in messages:
                self.send(msg=msg)


g_worker = Receptionist()


if __name__ == '__main__':
    Log.info(msg='>>> starting receptionist ...')
    g_worker.start()
    Log.info(msg='>>> receptionist exists.')
