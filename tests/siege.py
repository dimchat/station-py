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

import multiprocessing
import threading
import time
from typing import List

from dimp import PrivateKey
from dimp import MetaType, Meta, Document
from dimp import NetworkType, ID
from dimp import User

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Log, Logging
from libs.utils import Runner
from libs.database import Storage
from libs.common import CommonFacebook
from libs.client import Server, Terminal, ClientMessenger

from etc.config import base_dir
from robots.config import g_facebook, dims_connect


class Soldier(Runner, Logging):

    def __init__(self, client_id: ID):
        super().__init__()
        # check private keys
        facebook = CommonFacebook()
        keys = facebook.private_key_for_signature(identifier=client_id)
        assert len(keys) > 0, 'private key not found: %s' % client_id
        keys = facebook.private_keys_for_decryption(identifier=client_id)
        assert len(keys) > 0, 'private key not found: %s' % client_id
        user = facebook.user(identifier=client_id)
        assert user is not None, 'failed to get user: %s' % user
        facebook.current_user = user
        # client
        client = Terminal()
        messenger = ClientMessenger(facebook=facebook)
        facebook.messenger = messenger
        self.__terminal = client
        self.__messenger = messenger
        self.__user = user
        self.__server = None
        self.__time_to_retreat = time.time() + 32

    def __del__(self):
        self.warning(msg='soldier down: %s' % self.user)

    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s>%s%s</%s module="%s">' % (cname, self.user, self.server, cname, mod)

    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s>%s%s</%s module="%s">' % (cname, self.user, self.server, cname, mod)

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @property
    def terminal(self) -> Terminal:
        return self.__terminal

    @property
    def user(self) -> User:
        return self.__user

    @property
    def server(self) -> Server:
        return self.__server

    @property  # Override
    def running(self) -> bool:
        if super().running:
            return time.time() < self.__time_to_retreat

    # Override
    def setup(self):
        super().setup()
        self.info(msg='setup client: %s' % self)
        dims_connect(terminal=self.terminal, server=self.server, user=self.user, messenger=self.messenger)

    # Override
    def finish(self):
        terminal = self.terminal
        terminal.stop()
        self.info(msg='finish client: %s' % self)
        super().finish()

    # Override
    def process(self) -> bool:
        return False

    def attack(self, target: ID, host: str, port: int = 9394) -> threading.Thread:
        self.__server = Server(identifier=target, host=host, port=port)
        thr = threading.Thread(target=self.run, daemon=True)
        thr.start()
        return thr


class Sergeant(Logging):

    LANDING_POINT = 'normandy'

    UNITS = 10  # threads count

    def __init__(self, client_id: ID, offset: int):
        super().__init__()
        self.__cid = str(client_id)
        self.__offset = offset
        self.__target = None
        self.__host = None
        self.__port = 0

    def run(self):
        cid = ID.parse(identifier=self.__cid)
        target = ID.parse(identifier=self.__target)
        host = self.__host
        port = self.__port
        threads = []
        for i in range(self.UNITS):
            self.warning(msg='**** thread starts (%d + %d): %s' % (self.__offset, i, cid))
            soldier = Soldier(client_id=cid)
            thr = soldier.attack(target=target, host=host, port=port)
            threads.append(thr)
            self.__offset += self.UNITS
        for thr in threads:
            thr.join()
            self.warning(msg='**** thread stopped: %s' % thr)

    def attack(self, target: ID, host: str, port: int = 9394) -> multiprocessing.Process:
        self.__target = str(target)
        self.__host = host
        self.__port = port
        proc = multiprocessing.Process(target=self.run, daemon=True)
        proc.start()
        return proc

    @classmethod
    def training(cls, sn: int) -> ID:
        """ create new robot """
        seed = 'soldier%03d' % sn
        # 1. generate private key
        pri_key = PrivateKey.generate(algorithm=PrivateKey.RSA)
        # 2. generate meta
        meta = Meta.generate(version=MetaType.DEFAULT, key=pri_key, seed=seed)
        # 3. generate ID
        identifier = ID.generate(meta=meta, network=NetworkType.ROBOT)
        print('\n    Net ID: %s\n' % identifier)
        # 4. save private key & meta
        g_facebook.save_private_key(key=pri_key, identifier=identifier)
        g_facebook.save_meta(meta=meta, identifier=identifier)
        # 5. create visa
        visa = Document.create(doc_type=Document.VISA, identifier=identifier)
        visa.name = 'Soldier %03d @%s' % (sn, cls.LANDING_POINT)
        # 6. sign and save visa
        visa.sign(private_key=pri_key)
        g_facebook.save_document(document=visa)
        return identifier


class Colonel(Runner, Logging):

    TROOPS = 16  # progresses count

    def __init__(self):
        super().__init__()
        self.__soldiers: List[ID] = []
        self.__offset = 0
        # target station
        self.__sid = None
        self.__host = None
        self.__port = 0

    def attack(self, target: ID, host: str, port: int = 9394):
        self.__sid = target
        self.__host = host
        self.__port = port
        self.run()

    # Override
    def setup(self):
        super().setup()
        # load soldiers
        path = os.path.join(base_dir, 'soldiers.txt')
        text = Storage.read_text(path=path)
        if text is not None:
            array = text.splitlines()
            for item in array:
                if len(item) < 45 or len(item) > 55:
                    self.error(msg='*** ID error: %s' % item)
                    continue
                cid = ID.parse(identifier=item)
                if cid is not None:
                    self.__soldiers.append(cid)
        # count
        count = len(self.__soldiers)
        if count < self.TROOPS:
            # more soldiers
            for i in range(count, self.TROOPS):
                cid = Sergeant.training(sn=i)
                assert cid is not None, 'failed to train new soldier'
                self.__soldiers.append(cid)
                # save to '.dim/soldiers.txt'
                line = '%s\n' % cid
                Storage.append_text(text=line, path=path)

    # Override
    def process(self) -> bool:
        server_id = self.__sid
        host = self.__host
        port = self.__port
        processes = []
        for i in range(self.TROOPS):
            soldier = self.__soldiers[i]
            self.warning(msg='**** process starts [%d]: %s -> %s (%s:%d)' % (i, soldier, server_id, host, port))
            sergeant = Sergeant(client_id=soldier, offset=self.__offset)
            proc = sergeant.attack(target=server_id, host=host, port=port)
            processes.append(proc)
            time.sleep(1)
            self.__offset += Sergeant.UNITS
        for proc in processes:
            proc.join()
            self.warning(msg='**** process stopped: %s' % proc)
        # return False to have a rest
        return False

    # Override
    def _idle(self):
        print('====================================================')
        print('== All soldiers retreated, retry after 16 seconds...')
        print('====================================================')
        print('sleeping ...')
        for z in range(16):
            print('%d ..zzZZ' % z)
            time.sleep(1)
        print('wake up.')
        print('====================================================')
        print('== Attack !!!')
        print('====================================================')


# Log.LEVEL = Log.DEBUG
# Log.LEVEL = Log.DEVELOP
Log.LEVEL = Log.RELEASE

Sergeant.LANDING_POINT = 'normandy'
Sergeant.UNITS = 10
Colonel.TROOPS = 10

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
test_ip = test_station[0]
test_id = test_station[1]


if __name__ == '__main__':
    sid = ID.parse(identifier=test_id)
    print('**** Start testing %s ...' % sid)
    Colonel().attack(target=sid, host=test_ip, port=9394)
