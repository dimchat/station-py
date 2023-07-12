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
import time
from typing import Optional

from dimples import ID
from dimples import AccountDBI, MessageDBI, SessionDBI
from dimples.common import ProviderInfo
from dimples.common import ANSFactory
from dimples.common import AddressNameServer
from dimples.database import Storage
from dimples.server import FilterManager
from dimples.server import BroadcastRecipientManager

from libs.utils import Singleton
from libs.common import Config
from libs.common import CommonFacebook
from libs.database import Database
from libs.server import ServerMessenger, ServerPacker, ServerProcessor
from libs.server import ServerSession
from libs.server import PushCenter, DefaultPushService
from libs.server import Dispatcher, BlockFilter, MuteFilter
from libs.server import Emitter, Monitor


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
        self.emitter: Optional[Emitter] = None


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
    # filters
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
    user = facebook.user(identifier=current_user)
    assert user is not None, 'failed to get current user: %s' % current_user
    visa = user.visa
    if visa is not None:
        # refresh visa
        now = time.time()
        visa.set_property(key='time', value=now)
        visa.sign(private_key=sign_key)
        facebook.save_document(document=visa)
    facebook.current_user = user
    return facebook


def create_dispatcher(shared: GlobalVariable) -> Dispatcher:
    """ Step 4: create dispatcher """
    dispatcher = Dispatcher()
    dispatcher.mdb = shared.mdb
    dispatcher.sdb = shared.sdb
    dispatcher.facebook = shared.facebook
    return dispatcher


def create_emitter(shared: GlobalVariable) -> Emitter:
    """ Step 5. create emitter """
    messenger = create_messenger(facebook=shared.facebook, database=shared.mdb, session=None)
    emitter = Emitter(messenger=messenger)
    shared.emitter = emitter
    return emitter


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


def create_ans(config: Config) -> AddressNameServer:
    """ Step 6: create ANS """
    ans = AddressNameServer()
    factory = ID.factory()
    ID.register(factory=ANSFactory(factory=factory, ans=ans))
    # load ANS records from 'config.ini'
    ans_records = config.ans_records
    if ans_records is not None:
        ans.fix(records=ans_records)
    # set bots to receive message for 'everyone@everywhere'
    bots = set()
    se = ans.identifier(name='archivist')  # Search Engine
    if se is not None:
        bots.add(se)
    if len(bots) > 0:
        manager = BroadcastRecipientManager()
        manager.station_bots = bots
    return ans


def create_apns(shared: GlobalVariable) -> PushCenter:
    """ Step 7: create push center """
    facebook = shared.facebook
    emitter = shared.emitter
    center = PushCenter()
    keeper = center.badge_keeper
    center.service = DefaultPushService(badge_keeper=keeper, facebook=facebook, emitter=emitter)
    return center


def create_monitor(shared: GlobalVariable) -> Monitor:
    """ Step 8: create monitor """
    emitter = shared.emitter
    assert emitter is not None, 'emitter not set'
    monitor = Monitor()
    monitor.emitter = emitter
    monitor.start()
    return monitor


def prepare_server(server_name: str, default_config: str) -> GlobalVariable:
    # create global variable
    shared = GlobalVariable()
    # Step 1: load config
    config = create_config(app_name=server_name, default_config=default_config)
    shared.config = config
    # Step 2: create database
    db = create_database(config=config)
    shared.adb = db
    shared.mdb = db
    shared.sdb = db
    shared.database = db
    # Step 3: create facebook
    sid = config.station_id
    assert sid is not None, 'current station ID not set: %s' % config
    facebook = create_facebook(database=db, current_user=sid)
    shared.facebook = facebook
    # Step 4: create dispatcher
    create_dispatcher(shared=shared)
    # Step 5. create emitter
    create_emitter(shared=shared)
    # Step 6: create ANS
    create_ans(config=config)
    # Step 7: create push center
    create_apns(shared=shared)
    # Step 8: create monitor
    create_monitor(shared=shared)
    # OK
    return shared
