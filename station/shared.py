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

from dimples import Address, ID, IDFactory
from dimples import AccountDBI, MessageDBI, SessionDBI
from dimples.common import ProviderInfo
from dimples.common import AddressNameServer
from dimples.database import Storage
from dimples.server import FilterManager

from libs.utils import Singleton
from libs.common import Config
from libs.common import CommonFacebook
from libs.database import Database
from libs.server import PushCenter, Pusher, Monitor
from libs.server import Dispatcher, BlockFilter, MuteFilter
from libs.push import NotificationPusher
from libs.push import ApplePushNotificationService
from libs.push import AndroidPushNotificationService


class ANSFactory(IDFactory):

    def __init__(self, factory: IDFactory, ans: AddressNameServer):
        super().__init__()
        self.__origin = factory
        self.__ans = ans

    # Override
    def generate_id(self, meta, network: int, terminal: Optional[str] = None) -> ID:
        return self.__origin.generate_id(meta=meta, network=network, terminal=terminal)

    # Override
    def create_id(self, name: Optional[str], address: Address, terminal: Optional[str] = None) -> ID:
        return self.__origin.create_id(address=address, name=name, terminal=terminal)

    # Override
    def parse_id(self, identifier: str) -> Optional[ID]:
        # try ANS record
        aid = self.__ans.identifier(name=identifier)
        if aid is None:
            # parse by original factory
            aid = self.__origin.parse_id(identifier=identifier)
        return aid


@Singleton
class GlobalVariable:

    def __init__(self):
        super().__init__()
        self.config: Optional[Config] = None
        self.adb: Optional[AccountDBI] = None
        self.mdb: Optional[MessageDBI] = None
        self.sdb: Optional[SessionDBI] = None
        self.database: Optional[Database] = None
        self.facebook: Optional[CommonFacebook] = None
        self.pusher: Optional[Pusher] = None


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


def create_config(app_name: str, default_config: str) -> Config:
    """ Step 1: load config """
    cmd = sys.argv[0]
    try:
        opts, args = getopt.getopt(args=sys.argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help(cmd=cmd, app_name=app_name, default_config=default_config)
        sys.exit(1)
    # check options
    ini_file = None
    for opt, arg in opts:
        if opt == '--config':
            ini_file = arg
        else:
            show_help(cmd=cmd, app_name=app_name, default_config=default_config)
            sys.exit(0)
    # check config file path
    if ini_file is None:
        ini_file = default_config
    if not Storage.exists(path=ini_file):
        show_help(cmd=cmd, app_name=app_name, default_config=default_config)
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load config from file
    config = Config.load(file=ini_file)
    print('>>> config loaded: %s => %s' % (ini_file, config))
    return config


def create_database(config: Config) -> Database:
    """ Step 2: create database """
    root = config.database_root
    public = config.database_public
    private = config.database_private
    # create database
    db = Database(root=root, public=public, private=private)
    db.show_info()
    db.clear_socket_addresses()  # clear before station start
    # default provider
    provider = ProviderInfo.GSP
    # add neighbors
    neighbors = config.neighbors
    for node in neighbors:
        print('adding neighbor node: %s' % node)
        db.add_station(identifier=None, host=node.host, port=node.port, provider=provider)
    # filter
    man = FilterManager()
    man.block_filter = BlockFilter(database=db)
    man.mute_filter = MuteFilter(database=db)
    return db


def create_facebook(database: AccountDBI, current_user: ID) -> CommonFacebook:
    """ Step 3: create facebook """
    facebook = CommonFacebook(database=database)
    # make sure private keys exists
    sign_key = facebook.private_key_for_visa_signature(identifier=current_user)
    msg_keys = facebook.private_keys_for_decryption(identifier=current_user)
    assert sign_key is not None, 'failed to get sign key for current user: %s' % current_user
    assert msg_keys is not None and len(msg_keys) > 0, 'failed to get msg keys: %s' % current_user
    print('set current user: %s' % current_user)
    facebook.current_user = facebook.user(identifier=current_user)
    monitor = Monitor()
    monitor.facebook = facebook
    return facebook


def create_ans(config: Config) -> AddressNameServer:
    """ Step 4: create ANS """
    ans = AddressNameServer()
    factory = ID.factory()
    ID.register(factory=ANSFactory(factory=factory, ans=ans))
    # load ANS records from 'config.ini'
    ans_records = config.ans_records
    if ans_records is not None:
        ans.fix(records=ans_records)
    return ans


def create_pusher(shared: GlobalVariable) -> Pusher:
    """ Step 5: create pusher """
    pusher = NotificationPusher(facebook=shared.facebook)
    shared.pusher = pusher
    # create push services for PushCenter
    center = PushCenter()
    config = shared.config
    # 1. add push service: APNs
    credentials = config.get_string(section='push', option='apns_credentials')
    use_sandbox = config.get_boolean(section='push', option='apns_use_sandbox')
    topic = config.get_string(section='push', option='apns_topic')
    print('APNs: credentials=%s, use_sandbox=%d, topic=%s' % (credentials, use_sandbox, topic))
    if credentials is not None and len(credentials) > 0:
        apple = ApplePushNotificationService(credentials=credentials,
                                             use_sandbox=use_sandbox)
        if topic is not None and len(topic) > 0:
            apple.topic = topic
        apple.delegate = shared.database
        center.add_service(service=apple)
    # 2. add push service: JPush
    app_key = config.get_string(section='push', option='app_key')
    master_secret = config.get_string(section='push', option='master_secret')
    production = config.get_boolean(section='push', option='apns_production')
    print('APNs: app_key=%s, master_secret=%s, production=%s' % (app_key, master_secret, production))
    if app_key is not None and len(app_key) > 0 and master_secret is not None and len(master_secret) > 0:
        android = AndroidPushNotificationService(app_key=app_key,
                                                 master_secret=master_secret,
                                                 apns_production=production)
        center.add_service(service=android)
    # start PushCenter
    center.start()
    return pusher


def create_dispatcher(shared: GlobalVariable) -> Dispatcher:
    """ Step 6: create dispatcher """
    dispatcher = Dispatcher()
    dispatcher.mdb = shared.mdb
    dispatcher.sdb = shared.sdb
    dispatcher.facebook = shared.facebook
    dispatcher.pusher = shared.pusher
    dispatcher.start()
    return dispatcher
