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
from dimples import AccountDBI, MessageDBI, SessionDBI
from dimples.database import Storage

from libs.utils import Singleton
from libs.common import Config
from libs.common import CommonFacebook
from libs.database import Database
from libs.server import PushCenter, Pusher
from libs.server import Dispatcher
from libs.server import UserDeliver, BotDeliver, StationDeliver
from libs.server import GroupDeliver, BroadcastDeliver
from libs.server import DeliverWorker, DefaultRoamer
from libs.server import AddressNameService, AddressNameServer, ANSFactory
from libs.push import NotificationPusher
from libs.push import ApplePushNotificationService
from libs.push import AndroidPushNotificationService


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
    # check config filepath
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
    # add neighbors
    neighbors = config.neighbors
    for node in neighbors:
        print('adding neighbor node: (%s:%d), ID="%s"' % (node.host, node.port, node.identifier))
        db.add_neighbor(host=node.host, port=node.port, identifier=node.identifier)
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
    return facebook


def create_ans(config: Config) -> AddressNameService:
    """ Step 4: create ANS """
    ans = AddressNameServer()
    factory = ID.factory()
    ID.register(factory=ANSFactory(factory=factory, ans=ans))
    # load ANS records from 'config.ini'
    ans.fix(fixed=config.ans_records)
    return ans


def create_pusher(shared: GlobalVariable) -> Pusher:
    """ Step 5: create pusher """
    pusher = NotificationPusher(facebook=shared.facebook)
    shared.pusher = pusher
    # create push services for PushCenter
    center = PushCenter()
    config = shared.config
    # 1. add push service: APNs
    credentials = config.get_str(section='push', option='apns_credentials')
    use_sandbox = config.get_bool(section='push', option='apns_use_sandbox')
    topic = config.get_str(section='push', option='apns_topic')
    if credentials is not None and len(credentials) > 0:
        apple = ApplePushNotificationService(credentials=credentials,
                                             use_sandbox=use_sandbox)
        if topic is not None and len(topic) > 0:
            apple.topic = topic
        apple.delegate = shared.database
        center.add_service(service=apple)
    # 2. add push service: JPush
    app_key = config.get_str(section='push', option='app_key')
    master_secret = config.get_str(section='push', option='master_secret')
    production = config.get_bool(section='push', option='apns_production')
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
    dispatcher.database = shared.mdb
    dispatcher.facebook = shared.facebook
    # set base deliver delegates
    user_deliver = UserDeliver(database=shared.mdb, pusher=shared.pusher)
    bot_deliver = BotDeliver(database=shared.mdb)
    station_deliver = StationDeliver()
    dispatcher.set_user_deliver(deliver=user_deliver)
    dispatcher.set_bot_deliver(deliver=bot_deliver)
    dispatcher.set_station_deliver(deliver=station_deliver)
    # set special deliver delegates
    group_deliver = GroupDeliver(facebook=shared.facebook)
    broadcast_deliver = BroadcastDeliver(database=shared.sdb)
    dispatcher.set_group_deliver(deliver=group_deliver)
    dispatcher.set_broadcast_deliver(deliver=broadcast_deliver)
    # set roamer & worker
    roamer = DefaultRoamer(database=shared.mdb)
    worker = DeliverWorker(database=shared.sdb, facebook=shared.facebook)
    dispatcher.set_roamer(roamer=roamer)
    dispatcher.set_deliver_worker(worker=worker)
    # start all delegates
    user_deliver.start()
    bot_deliver.start()
    station_deliver.start()
    roamer.start()
    return dispatcher
