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
import threading
from typing import Optional, List

from dimples import ID
from dimples import Station
from dimples.common import AccountDBI, MessageDBI, SessionDBI

from libs.utils import Log
from libs.utils import Singleton
from libs.utils.nlp import ChatBot, Tuling, XiaoI
from libs.common import CommonFacebook, CommonPacker
from libs.common import Config
from libs.database import Storage
from libs.database import Database
from libs.client import ClientSession, ClientMessenger
from libs.client import Terminal


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


def init_database(shared: GlobalVariable):
    config = shared.config
    root = config.database_root
    public = config.database_public
    private = config.database_private
    # create database
    db = Database(root=root, public=public, private=private)
    db.show_info()
    shared.adb = db
    shared.mdb = db
    shared.sdb = db
    shared.database = db


def init_facebook(shared: GlobalVariable, current_user: ID) -> CommonFacebook:
    # set account database
    facebook = CommonFacebook()
    facebook.database = shared.adb
    shared.facebook = facebook
    # set current user
    # make sure private key exists
    assert facebook.private_key_for_visa_signature(identifier=current_user) is not None, \
        'failed to get sign key for current user: %s' % current_user
    print('set current user: %s' % current_user)
    facebook.current_user = facebook.user(identifier=current_user)
    return facebook


def create_messenger(user: ID, host: str, port: int, processor_class) -> ClientMessenger:
    shared = GlobalVariable()
    facebook = shared.facebook
    # 0. create station with remote host & port
    station = Station(host=host, port=port)
    station.data_source = facebook
    # 1. create session with SessionDB
    session = ClientSession(station=station, database=shared.sdb)
    session.set_identifier(identifier=user)
    # 2. create messenger with session and MessageDB
    messenger = ClientMessenger(session=session, facebook=facebook, database=shared.mdb)
    # 3. create packer, processor for messenger
    #    they have weak references to facebook & messenger
    messenger.packer = CommonPacker(facebook=facebook, messenger=messenger)
    messenger.processor = processor_class(facebook=facebook, messenger=messenger)
    # 4. set weak reference to messenger
    session.messenger = messenger
    return messenger


def show_help(cmd: str, app_name: str, default_config: str):
    print('')
    print('    %s' % app_name)
    print('')
    print('usages:')
    print('    %s [--config=<FILE>] <BID>' % cmd)
    print('    %s [-h|--help]' % cmd)
    print('')
    print('optional arguments:')
    print('    --config        config file path (default: "%s")' % default_config)
    print('    --help, -h      show this help message and exit')
    print('')


def main(argv: List[str], app_name: str, default_config: str, processor_class):
    try:
        opts, args = getopt.getopt(args=argv[1:],
                                   shortopts='hf:',
                                   longopts=['help', 'config='])
    except getopt.GetoptError:
        show_help(cmd=argv[0], app_name=app_name, default_config=default_config)
        sys.exit(1)
    # check options
    ini_file = None
    for opt, arg in opts:
        if opt == '--config':
            ini_file = arg
        else:
            show_help(cmd=argv[0], app_name=app_name, default_config=default_config)
            sys.exit(0)
    # check arguments
    if len(args) == 1:
        identifier = ID.parse(identifier=args[0])
        if identifier is None:
            show_help(cmd=argv[0], app_name=app_name, default_config=default_config)
            print('')
            print('!!! Bot ID error: %s' % args[0])
            print('')
            sys.exit(0)
    else:
        show_help(cmd=argv[0], app_name=app_name, default_config=default_config)
        sys.exit(0)
    # check config filepath
    if ini_file is None:
        ini_file = default_config
    if not Storage.exists(path=ini_file):
        show_help(cmd=argv[0], app_name=app_name, default_config=default_config)
        print('')
        print('!!! config file not exists: %s' % ini_file)
        print('')
        sys.exit(0)
    # load config
    config = Config.load(file=ini_file)
    # initializing
    print('[DB] init with config: %s => %s' % (ini_file, config))
    shared = GlobalVariable()
    shared.config = config
    init_database(shared=shared)
    init_facebook(shared=shared, current_user=identifier)
    # create messenger and connect to station (host:port)
    host = config.station_host
    port = config.station_port
    messenger = create_messenger(user=identifier, host=host, port=port, processor_class=processor_class)
    # create and start terminal
    terminal = Terminal(messenger=messenger)
    messenger.terminal = terminal
    thread = threading.Thread(target=terminal.run, daemon=False)
    thread.start()


#
#   Natural Language Processing
#   ~~~~~~~~~~~~~~~~~~~~~~~~~~~
#


def chat_bots(names: List[str], shared: GlobalVariable) -> List[ChatBot]:
    """
        Chat Bots
        ~~~~~~~~~

        Chat bots from 3rd-party
    """
    bots = []
    for n in names:
        b = chat_bot(name=n, shared=shared)
        if b is not None:
            bots.append(b)
    return bots


def chat_bot(name: str, shared: GlobalVariable) -> Optional[ChatBot]:
    config = shared.config
    if 'tuling' == name:
        # Tuling ChatBot
        path = config.get_str(section='nlp', option='tuling_keys')
        if path is None:
            Log.error(msg='Tuling keys not config')
            return None
        tuling_keys = Storage.read_json(path=path)
        api_key = tuling_keys.get('api_key')
        assert api_key is not None, 'Tuling keys error: %s' % tuling_keys
        tuling = Tuling(api_key=api_key)
        # config ignores
        tuling_ignores = config.get_str(section='nlp', option='tuling_ignores')
        array = tuling_ignores.split(',')
        for item in array:
            value = int(item)
            if value not in tuling.ignores:
                tuling.ignores.append(value)
        return tuling
    elif 'xiaoi' == name:
        # XiaoI ChatBot
        path = config.get_str(section='nlp', option='xiaoi_keys')
        if path is None:
            Log.error(msg='XiaoI keys not config')
            return None
        xiaoi_keys = Storage.read_json(path=path)
        app_key = xiaoi_keys.get('app_key')
        app_secret = xiaoi_keys.get('app_secret')
        assert app_key is not None and app_secret is not None, 'XiaoI keys error: %s' % xiaoi_keys
        xiaoi = XiaoI(app_key=app_key, app_secret=app_secret)
        # config ignores
        xiaoi_ignores = config.get_str(section='nlp', option='xiaoi_ignores')
        array = xiaoi_ignores.split(',')
        for item in array:
            value = item.strip()
            if value not in xiaoi.ignores:
                xiaoi.ignores.append(value)
        return xiaoi
    else:
        raise NotImplementedError('unknown chat bot: %s' % name)
