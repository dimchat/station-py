# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2022 Albert Moky
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

import getopt
import sys
from typing import Optional

from dimples import ID
from dimples import Document
from dimples import AccountDBI, MessageDBI, SessionDBI
from dimples.common import ProviderInfo
from dimples.group import SharedGroupManager
from dimples.server import FilterManager

from libs.utils import Path, Log
from libs.utils import Singleton
from libs.utils import Config
from libs.common import ExtensionLoader
from libs.common import CommonFacebook
from libs.database.redis import RedisConnector
from libs.database import DbInfo
from libs.database import Database

from libs.server import ServerArchivist
from libs.server import ServerChecker
from libs.server import ServerFacebook
from libs.server import ServerMessenger, ServerPacker, ServerProcessor
from libs.server import ServerSession
from libs.server import PushCenter, DefaultPushService
from libs.server import MessageDeliver, Roamer
from libs.server import Dispatcher, BlockFilter, MuteFilter
from libs.server import ServerEmitter, Monitor


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.__config: Optional[Config] = None
        self.__adb: Optional[AccountDBI] = None
        self.__mdb: Optional[MessageDBI] = None
        self.__sdb: Optional[SessionDBI] = None
        self.__database: Optional[Database] = None
        self.__facebook: Optional[ServerFacebook] = None
        self.__messenger: Optional[ServerMessenger] = None  # only for entity checker
        self.__emitter: Optional[ServerEmitter] = None

    @property
    def config(self) -> Config:
        return self.__config

    @property
    def adb(self) -> AccountDBI:
        return self.__adb

    @property
    def mdb(self) -> MessageDBI:
        return self.__mdb

    @property
    def sdb(self) -> SessionDBI:
        return self.__sdb

    @property
    def database(self) -> Database:
        return self.__database

    @property
    def facebook(self) -> ServerFacebook:
        return self.__facebook

    @property
    def messenger(self) -> ServerMessenger:
        return self.__messenger

    @messenger.setter
    def messenger(self, transceiver: ServerMessenger):
        self.__messenger = transceiver
        # set for group manager
        man = SharedGroupManager()
        man.messenger = transceiver
        # set for entity checker
        checker = self.facebook.checker
        assert isinstance(checker, ServerChecker), 'entity checker error: %s' % checker
        checker.messenger = transceiver

    async def prepare(self, config: Config):
        #
        #  Step 0: load config
        #
        ExtensionLoader().run()
        ans_records = config.ans_records
        if ans_records is not None:
            # load ANS records from 'config.ini'
            CommonFacebook.ans.fix(records=ans_records)
        self.__config = config
        #
        #  Step 1: create database
        #
        database = await create_database(config=config)
        self.__adb = database
        self.__mdb = database
        self.__sdb = database
        self.__database = database
        #
        #  Step 2: create facebook
        #
        facebook = await create_facebook(database=database)
        self.__facebook = facebook
        #
        #  Step 3: prepare dispatcher
        #
        deliver = MessageDeliver(database=database, facebook=facebook)
        roamer = Roamer(database=database, deliver=deliver)
        dispatcher = Dispatcher()
        dispatcher.mdb = database
        dispatcher.sdb = database
        dispatcher.facebook = facebook
        dispatcher.deliver = deliver
        dispatcher.roamer = roamer
        #
        #  Step 4. create emitter
        #
        messenger = create_messenger(facebook=facebook, database=database, session=None)
        # this messenger is only for encryption, so don't need a session
        emitter = ServerEmitter(messenger=messenger)
        self.__emitter = emitter
        # server check don't need a session to send message too
        checker = facebook.checker
        assert isinstance(checker, ServerChecker), 'entity checker error: %s' % checker
        checker.messenger = messenger
        #
        #  Step 5: prepare push center
        #
        center = PushCenter()
        keeper = center.badge_keeper
        center.service = DefaultPushService(badge_keeper=keeper, facebook=facebook, emitter=emitter)
        #
        #  Step 6: prepare monitor
        #
        monitor = Monitor()
        monitor.emitter = emitter

    async def login(self, current_user: ID):
        facebook = self.facebook
        # make sure private keys exists
        sign_key = await facebook.private_key_for_visa_signature(identifier=current_user)
        msg_keys = await facebook.private_keys_for_decryption(identifier=current_user)
        assert sign_key is not None, 'failed to get sign key for current user: %s' % current_user
        assert len(msg_keys) > 0, 'failed to get msg keys: %s' % current_user
        Log.info(msg='set current user: %s' % current_user)
        user = await facebook.get_user(identifier=current_user)
        assert user is not None, 'failed to get current user: %s' % current_user
        visa = await user.visa
        if visa is not None:
            # refresh visa
            visa = Document.parse(document=visa.copy_dictionary())
            visa.sign(private_key=sign_key)
            await facebook.save_document(document=visa)
        await facebook.set_current_user(user=user)


def create_redis_connector(config: Config) -> Optional[RedisConnector]:
    redis_enable = config.get_boolean(section='redis', option='enable')
    if redis_enable:
        # create redis connector
        host = config.get_string(section='redis', option='host')
        if host is None:
            host = 'localhost'
        port = config.get_integer(section='redis', option='port')
        if port is None or port <= 0:
            port = 6379
        username = config.get_string(section='redis', option='username')
        password = config.get_string(section='redis', option='password')
        return RedisConnector(host=host, port=port, username=username, password=password)


async def create_database(config: Config) -> Database:
    """ create database with directories """
    root = config.database_root
    public = config.database_public
    private = config.database_private
    redis_conn = create_redis_connector(config=config)
    info = DbInfo(redis_connector=redis_conn, root_dir=root, public_dir=public, private_dir=private)
    # create database
    db = Database(info=info)
    db.show_info()
    # update neighbor stations (default provider)
    provider = ProviderInfo.GSP
    neighbors = config.neighbors
    if len(neighbors) > 0:
        await db.remove_stations(provider=provider)
        for node in neighbors:
            Log.info(msg='adding neighbor node: %s' % node)
            await db.add_station(identifier=None, host=node.host, port=node.port, provider=provider)
    # clear before station start
    await db.clear_socket_addresses()
    # filters
    man = FilterManager()
    man.block_filter = BlockFilter(database=db)
    man.mute_filter = MuteFilter(database=db)
    # OK
    return db


async def create_facebook(database: AccountDBI) -> ServerFacebook:
    """ create facebook """
    facebook = ServerFacebook(database=database)
    facebook.archivist = ServerArchivist(facebook=facebook, database=database)
    facebook.checker = ServerChecker(facebook=facebook, database=database)
    # set for group manager
    man = SharedGroupManager()
    man.facebook = facebook
    return facebook


def create_messenger(facebook: CommonFacebook, database: MessageDBI,
                     session: Optional[ServerSession]) -> ServerMessenger:
    # 1. create messenger with session and MessageDB
    messenger = ServerMessenger(session=session, facebook=facebook, database=database)
    # 2. create packer, processor, filter for messenger
    #    they have weak references to session, facebook & messenger
    messenger.packer = ServerPacker(facebook=facebook, messenger=messenger)
    messenger.processor = ServerProcessor(facebook=facebook, messenger=messenger)
    # 3. set weak reference messenger in session
    if session is not None:
        session.messenger = messenger
    return messenger


def show_help(app_name: str, default_config: str):
    cmd = sys.argv[0]
    print('')
    print('    %s' % app_name)
    print('')
    print('usages:')
    print('    %s [--config=<FILE>]' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('optional arguments:')
    print('    --config        config file path (default: "%s")' % default_config)
    print('    --help, -h      show this help message and exit')
    print('')


async def create_config(app_name: str, default_config: str) -> Config:
    """ load config """
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help(app_name=app_name, default_config=default_config)
        sys.exit(1)
    # check options
    ini_file = None
    for opt, arg in opts:
        if opt == '--config':
            ini_file = arg
        else:
            show_help(app_name=app_name, default_config=default_config)
            sys.exit(0)
    # check config file path
    if ini_file is None:
        ini_file = default_config
    if not await Path.exists(path=ini_file):
        show_help(app_name=app_name, default_config=default_config)
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load config from file
    config = Config.load(file=ini_file)
    print('>>> config loaded: %s => %s' % (ini_file, config))
    return config
