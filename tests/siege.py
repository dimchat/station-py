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

from dimples import PrivateKey
from dimples import MetaType, Meta, Document
from dimples import EntityType, ID
from dimples import Station

from dimples.utils import Path

path = Path.abs(path=__file__)
path = Path.dir(path=path)
path = Path.dir(path=path)
Path.add(path=path)

from libs.utils import Log, Logging
from libs.utils import Runnable, Runner
from libs.database import Storage
from libs.client import Terminal
from libs.client import ClientArchivist, ClientFacebook

from tests.runner import Runner as ThreadRunner
from tests.shared import GlobalVariable
from tests.shared import create_config, create_database
from tests.shared import create_facebook, create_messenger


#
# show logs
#
Log.LEVEL = Log.DEVELOP

soldiers_path = '/tmp/soldiers.txt'


DEFAULT_CONFIG = '/etc/dim/config.ini'

config = create_config(app_name='Siege', default_config=DEFAULT_CONFIG)
shared = GlobalVariable()
shared.config = config
create_database(shared=shared)


class Soldier(Logging, Runnable):

    def __init__(self, client_id: ID):
        super().__init__()
        self.__user = client_id
        self.__server = None

    def __del__(self):
        self.warning(msg='soldier down: %s' % self.user)

    def __str__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s>%s -> %s</%s module="%s">' % (cname, self.user, self.server, cname, mod)

    def __repr__(self) -> str:
        mod = self.__module__
        cname = self.__class__.__name__
        return '<%s>%s -> %s</%s module="%s">' % (cname, self.user, self.server, cname, mod)

    @property
    def user(self) -> ID:
        return self.__user

    @property
    def server(self) -> Station:
        return self.__server

    # Override
    async def run(self):
        client_id = self.user
        time_to_retreat = time.time() + 32
        # 1. preparing facebook
        facebook = await create_facebook(shared=shared, current_user=client_id)
        user = await facebook.get_user(identifier=client_id)
        assert user is not None, 'failed to get user: %s' % client_id
        facebook.current_user = user
        # 2. preparing messenger
        messenger = create_messenger(shared=shared, facebook=facebook)
        session = messenger.session
        server = session.station
        assert server is not None, 'failed to get station: %s' % session
        self.__server = messenger.session.station
        # 3. launch terminal
        terminal = Terminal(messenger=messenger)
        await terminal.start()
        Runner.async_task(coro=terminal.run())
        while True:
            await Runner.sleep(seconds=1.0)
            if not terminal.running:
                break
            elif time.time() > time_to_retreat:
                break
        # done
        await terminal.stop()

    def attack(self):
        Runner.sync_run(main=self.run())


class Sergeant(Logging):

    LANDING_POINT = 'normandy'

    UNITS = 10  # threads count

    def __init__(self, client_id: ID, offset: int):
        super().__init__()
        self.__cid = str(client_id)
        self.__offset = offset

    def run(self):
        cid = ID.parse(identifier=self.__cid)
        threads = []
        for i in range(self.UNITS):
            self.warning(msg='**** thread starts (%d + %d): %s' % (self.__offset, i, cid))
            soldier = Soldier(client_id=cid)
            thr = threading.Thread(target=soldier.attack(), daemon=True)
            thr.start()
            threads.append(thr)
            self.__offset += self.UNITS
        for thr in threads:
            thr.join()
            self.warning(msg='**** thread stopped: %s' % thr)

    def attack(self) -> multiprocessing.Process:
        proc = multiprocessing.Process(target=self.run)
        proc.daemon = True
        proc.start()
        return proc

    @classmethod
    def training(cls, sn: int) -> ID:
        """ create new bot """
        seed = 'soldier%03d' % sn
        # 1. generate private key
        pri_key = PrivateKey.generate(algorithm=PrivateKey.RSA)
        # 2. generate meta
        meta = Meta.generate(version=MetaType.DEFAULT, private_key=pri_key, seed=seed)
        # 3. generate ID
        identifier = ID.generate(meta=meta, network=EntityType.BOT)
        print('\n    Net ID: %s\n' % identifier)
        # 4. save private key & meta
        database = shared.adb
        facebook = ClientFacebook()
        # create archivist for facebook
        archivist = ClientArchivist(database=database)
        archivist.facebook = facebook
        facebook.archivist = archivist
        # facebook = CommonFacebook(database=shared.adb)
        database.save_private_key(key=pri_key, user=identifier)
        facebook.save_meta(meta=meta, identifier=identifier)
        # 5. create visa
        visa = Document.create(doc_type=Document.VISA, identifier=identifier)
        visa.name = 'Soldier %03d @%s' % (sn, cls.LANDING_POINT)
        # 6. sign and save visa
        visa.sign(private_key=pri_key)
        facebook.save_document(document=visa)
        return identifier


class Colonel(ThreadRunner, Logging):

    TROOPS = 16  # progresses count

    def __init__(self):
        super().__init__(interval=1.0)
        self.__soldiers: List[ID] = []
        self.__offset = 0

    def attack(self):
        self.run()

    # Override
    def setup(self):
        super().setup()
        # load soldiers
        text = Storage.read_text(path=soldiers_path)
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
                Storage.append_text(text=line, path=soldiers_path)

    # Override
    def process(self) -> bool:
        processes = []
        for i in range(self.TROOPS):
            soldier = self.__soldiers[i]
            self.warning(msg='**** process starts [%d]: %s' % (i, soldier))
            sergeant = Sergeant(client_id=soldier, offset=self.__offset)
            proc = sergeant.attack()
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
    # update config
    station = config.get('station')
    # assert isinstance(station, dict), 'config error: %s' % config
    # station['host'] = test_ip
    # station['id'] = test_id
    print('**** Start testing %s ...' % station)
    Colonel().attack()
