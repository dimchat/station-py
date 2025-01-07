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
from dimples.common import AccountDBI, MessageDBI, SessionDBI
from dimples.common import ProviderInfo
from dimples.group import SharedGroupManager
from dimples.client import ClientChecker

from libs.utils import Path, Log
from libs.utils import Singleton
from libs.utils import Config
from libs.common import ExtensionLoader
from libs.common import CommonFacebook
from libs.database.redis import RedisConnector
from libs.database import DbInfo
from libs.database import Database

from libs.client import ClientArchivist, ClientFacebook
from libs.client import ClientSession, ClientMessenger
from libs.client import Terminal


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.__config: Optional[Config] = None
        self.__adb: Optional[AccountDBI] = None
        self.__mdb: Optional[MessageDBI] = None
        self.__sdb: Optional[SessionDBI] = None
        self.__database: Optional[Database] = None
        self.__facebook: Optional[ClientFacebook] = None
        self.__messenger: Optional[ClientMessenger] = None

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
    def facebook(self) -> ClientFacebook:
        return self.__facebook

    @property
    def messenger(self) -> ClientMessenger:
        return self.__messenger

    @messenger.setter
    def messenger(self, transceiver: ClientMessenger):
        self.__messenger = transceiver
        # set for group manager
        man = SharedGroupManager()
        man.messenger = transceiver
        # set for entity checker
        checker = self.facebook.checker
        assert isinstance(checker, ClientChecker), 'entity checker error: %s' % checker
        checker.messenger = transceiver

    async def prepare(self, config: Config):
        #
        #  Step 1: load config
        #
        ExtensionLoader().run()
        ans_records = config.ans_records
        if ans_records is not None:
            # load ANS records from 'config.ini'
            CommonFacebook.ans.fix(records=ans_records)
        self.__config = config
        #
        #  Step 2: create database
        #
        database = await create_database(config=config)
        self.__adb = database
        self.__mdb = database
        self.__sdb = database
        self.__database = database
        #
        #  Step 3: create facebook
        #
        facebook = await create_facebook(database=database)
        self.__facebook = facebook

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
    #
    #  Update neighbor stations (default provider)
    #
    provider = ProviderInfo.GSP
    neighbors = config.neighbors
    if len(neighbors) > 0:
        # await db.remove_stations(provider=provider)
        # 1. remove vanished neighbors
        old_stations = await db.all_stations(provider=provider)
        for old in old_stations:
            found = False
            for item in neighbors:
                if item.port == old.port and item.host == old.host:
                    found = True
                    break
            if not found:
                Log.info(msg='removing neighbor station: %s, %s' % (old, provider))
                await db.remove_station(host=old.host, port=old.port, provider=provider)
        # 2. add new neighbors
        for node in neighbors:
            found = False
            for old in old_stations:
                if old.port == node.port and old.host == node.host:
                    found = True
                    break
            if not found:
                Log.info(msg='adding neighbor node: %s -> %s' % (node, provider))
                await db.add_station(identifier=None, host=node.host, port=node.port, provider=provider)
    # OK
    return db


async def create_facebook(database: AccountDBI) -> ClientFacebook:
    """ create facebook """
    facebook = ClientFacebook(database=database)
    facebook.archivist = ClientArchivist(facebook=facebook, database=database)
    facebook.checker = ClientChecker(facebook=facebook, database=database)
    # set for group manager
    man = SharedGroupManager()
    man.facebook = facebook
    return facebook


def show_help(app_name: str, default_config: str):
    cmd = sys.argv[0]
    print('')
    print('    %s' % app_name)
    print('')
    print('usages:')
    print('    %s [--config=<FILE>] [BID]' % cmd)
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
    # check config filepath
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
    # check arguments for Bot ID
    if len(args) == 1:
        identifier = ID.parse(identifier=args[0])
        if identifier is None:
            show_help(app_name=app_name, default_config=default_config)
            print('')
            print('!!! Bot ID error: %s' % args[0])
            print('')
            sys.exit(0)
        # set bot ID into config['bot']['id']
        bot = config.get('bot')
        if bot is None:
            bot = {}
            config['bot'] = bot
        bot['id'] = str(identifier)
    # OK
    return config


#
#   DIM Bot
#


def check_bot_id(config: Config, ans_name: str) -> bool:
    identifier = config.get_identifier(section='bot', option='id')
    if identifier is not None:
        # got it
        return True
    identifier = config.get_identifier(section='ans', option=ans_name)
    if identifier is None:
        # failed to get Bot ID
        return False
    bot_sec = config.get('bot')
    if bot_sec is None:
        bot_sec = {}
        config['bot'] = bot_sec
    bot_sec['id'] = str(identifier)
    return True


async def start_bot(ans_name: str, processor_class) -> Terminal:
    shared = GlobalVariable()
    config = shared.config
    if not check_bot_id(config=config, ans_name=ans_name):
        raise LookupError('Failed to get Bot ID: %s' % config)
    bot_id = config.get_identifier(section='bot', option='id')
    await shared.login(current_user=bot_id)
    # create terminal
    host = config.station_host
    port = config.station_port
    assert host is not None and port > 0, 'station config error: %s' % config
    client = BotClient(facebook=shared.facebook, database=shared.sdb, processor_class=processor_class)
    await client.connect(host=host, port=port)
    await client.run()
    return client


class BotClient(Terminal):

    def __init__(self, facebook: ClientFacebook, database: SessionDBI, processor_class):
        super().__init__(facebook=facebook, database=database)
        self.__processor_class = processor_class

    # Override
    def _create_processor(self, facebook: ClientFacebook, messenger: ClientMessenger):
        return self.__processor_class(facebook, messenger)

    # Override
    def _create_messenger(self, facebook: ClientFacebook, session: ClientSession) -> ClientMessenger:
        shared = GlobalVariable()
        messenger = ClientMessenger(session=session, facebook=facebook, database=shared.mdb)
        shared.messenger = messenger
        return messenger
