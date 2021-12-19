#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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
    Stress Testing
    ~~~~~~~~~~~~~~

"""

import sys
import os
import threading
import time

from dimp import ID, User
from startrek.fsm import Runner

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Log, Logging
from libs.common import CommonFacebook
from libs.client import Server, Terminal, ClientMessenger

from robots.config import g_facebook


class Soldier(Runner, Logging):

    def __init__(self, index: int, client_id: ID, server_id: ID, host: str, port: int = 9394):
        super().__init__()
        self.__time = 0
        self.__index = index
        self.__cid = client_id
        self.__sid = server_id
        self.__host = host
        self.__port = port
        self.__server = None
        self.__terminal = Terminal()
        self.__messenger = ClientMessenger()
        self.__facebook = CommonFacebook()

    def __del__(self):
        self.warning(msg='killing %s' % self)

    def __str__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s: %d| local="%s" remote="%s" />' % (clazz, self.__index, self.__cid, self.__sid)

    def __repr__(self) -> str:
        clazz = self.__class__.__name__
        return '<%s: %d| local="%s" remote="%s" />' % (clazz, self.__index, self.__cid, self.__sid)

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @property
    def facebook(self) -> CommonFacebook:
        return self.__facebook

    @property
    def terminal(self) -> Terminal:
        return self.__terminal

    @property
    def user(self) -> User:
        return self.facebook.user(identifier=self.__cid)

    @property
    def server(self) -> Server:
        srv = self.__server
        if srv is None:
            srv = Server(identifier=self.__sid, host=self.__host, port=self.__port)
            self.__server = srv
        return srv

    def start(self) -> threading.Thread:
        thr = threading.Thread(target=self.run)
        thr.start()
        return thr

    @property
    def running(self) -> bool:
        if super().running:
            return int(time.time()) < self.__time

    # Override
    def setup(self):
        super().setup()
        self.__time = int(time.time()) + 16
        self.info(msg='setup client: %s' % self)
        # create client and connect to the station
        server = self.server
        terminal = self.terminal
        facebook = self.facebook
        messenger = self.messenger
        facebook.current_user = self.user
        messenger.delegate = server
        messenger.facebook = facebook
        messenger.terminal = terminal
        server.messenger = messenger
        server.server_delegate = terminal
        # client
        terminal.messenger = messenger
        terminal.start(server=server)

    # Override
    def finish(self):
        terminal = self.terminal
        terminal.stop()
        self.info(msg='finish client: %s' % self)
        super().finish()

    # Override
    def process(self) -> bool:
        return False


# robots
all_soldiers = [ID.parse(identifier=did) for did in [
    'tide@2PeCKQWq3aYGvns5x2nf6gsyjgkcGcgtscW',
    'soldier1@2PgzJbRsmvxaBCh3ym7m3hb1PdKt1xwdf2Y',
    'soldier2@2PZg987298L5y9oNnuaMm6ZtBivUjtF2NqH',
    'soldier3@2PV3a4CTLKGJbtiGBnFJjroTwxqmHMWRAf4',
    'soldier4@2PmBTxstjxMhrY1bA4eBnae4xRduMCfJ8Q6',
    'soldier5@2PnbNB6n1R4GXKX9KARTnqNmrzuYM2G7SaV',
]]
# candidates
all_stations = [
    ('127.0.0.1', 'gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC'),
    ('106.52.25.169', 'gsp-s002@wpjUWg1oYDnkHh74tHQFPxii6q9j3ymnyW'),
    ('147.139.30.182', 'gsp-india@x15NniVboopEtD3d81cbUibftcewMxzZLw'),
    ('47.254.237.224', 'gsp-jlp@x8Eudmgq4rHvTm2ongrwk6BVdS1wuE7ctE'),
    ('149.129.234.145', 'gsp-yjd@wjPLYSyaZ7fe4aNL8DJAvHBNnFcgK76eYq'),
    ('', ''),
    ('', ''),
    ('', ''),
]
test_station = all_stations[4]


def open_fire():
    # current station IP & ID
    sip = test_station[0]
    sid = test_station[1]
    sid = ID.parse(identifier=sid)
    # test
    g_threads = []
    j = 0
    for i in range(10):
        for item in all_soldiers:
            keys = g_facebook.private_key_for_signature(identifier=item)
            assert len(keys) > 0, 'private key not found: %s' % item
            j += 1
            Log.info(msg='starting bot %d (%s)...' % (j, item))
            client = Soldier(index=j, client_id=item, server_id=sid, host=sip)
            thr = client.start()
            g_threads.append(thr)
        time.sleep(1)
    for thr in g_threads:
        thr.join()
        Log.info(msg='thread stop: %s' % thr)


if __name__ == '__main__':
    Log.info(msg='Starting ...')
    while True:
        open_fire()
        Log.info(msg='====================================================')
        Log.info(msg='== All soldiers retreated, retry after 16 seconds...')
        Log.info(msg='====================================================')
        Log.info(msg='sleeping ...')
        time.sleep(16)
        Log.info(msg='wake up.')
        Log.info(msg='====================================================')
        Log.info(msg='== Attack !!!')
        Log.info(msg='====================================================')
