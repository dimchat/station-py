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
from dimples import Station
from dimples.common import AccountDBI, MessageDBI, SessionDBI

from libs.utils import Path
from libs.utils import Singleton
from libs.utils import Config
from libs.common import CommonFacebook
from libs.database.redis import RedisConnector
from libs.database import DbInfo
from libs.database import Database
from libs.client import ClientArchivist, ClientFacebook
from libs.client import ClientSession, ClientMessenger, ClientProcessor, ClientPacker


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        self.adb: Optional[AccountDBI] = None
        self.mdb: Optional[MessageDBI] = None
        self.sdb: Optional[SessionDBI] = None
        self.database: Optional[Database] = None


def show_help(cmd: str, app_name: str, default_config: str):
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
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help(cmd=sys.argv[0], app_name=app_name, default_config=default_config)
        sys.exit(1)
    # check options
    ini_file = None
    for opt, arg in opts:
        if opt == '--config':
            ini_file = arg
        else:
            show_help(cmd=sys.argv[0], app_name=app_name, default_config=default_config)
            sys.exit(0)
    # check config file path
    if ini_file is None:
        ini_file = default_config
    if not await Path.exists(path=ini_file):
        show_help(cmd=sys.argv[0], app_name=app_name, default_config=default_config)
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load config
    print('>>> loading config file: %s' % ini_file)
    return Config.load(file=ini_file)


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
    return db


async def create_facebook(shared: GlobalVariable, current_user: ID) -> CommonFacebook:
    """ create facebook and set current user """
    # create facebook with account database
    facebook = ClientFacebook()
    # create archivist for facebook
    archivist = ClientArchivist(database=shared.adb)
    archivist.facebook = facebook
    facebook.archivist = archivist
    # set current user
    # make sure private key exists
    assert await facebook.private_key_for_visa_signature(identifier=current_user) is not None, \
        'failed to get sign key for current user: %s' % current_user
    print('set current user: %s' % current_user)
    facebook.current_user = await facebook.get_user(identifier=current_user)
    return facebook


def create_messenger(shared: GlobalVariable, facebook: CommonFacebook) -> ClientMessenger:
    """ create messenger and connect to station (host:port) """
    config = shared.config
    host = config.station_host
    port = config.station_port
    user = facebook.current_user
    # 1. create station with remote host & port
    station = Station(host=host, port=port)
    station.data_source = facebook
    # 2. create session with SessionDB
    session = ClientSession(station=station, database=shared.sdb)
    session.set_identifier(identifier=user.identifier)
    # 3. create messenger with session and MessageDB
    messenger = ClientMessenger(session=session, facebook=facebook, database=shared.mdb)
    # 4. create packer, processor for messenger
    #    they have weak references to facebook & messenger
    messenger.packer = ClientPacker(facebook=facebook, messenger=messenger)
    messenger.processor = ClientProcessor(facebook=facebook, messenger=messenger)
    # 5. set weak reference to messenger
    session.messenger = messenger
    return messenger
