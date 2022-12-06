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

from typing import Optional

from dimples import ID
from dimples import AccountDBI, MessageDBI, SessionDBI

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
    # add neighbors
    neighbors = config.neighbors
    for node in neighbors:
        print('adding neighbor node: (%s:%d), ID="%s"' % (node.host, node.port, node.identifier))
        db.add_neighbor(host=node.host, port=node.port, identifier=node.identifier)


def init_facebook(shared: GlobalVariable) -> CommonFacebook:
    # set account database
    facebook = CommonFacebook()
    facebook.database = shared.adb
    shared.facebook = facebook
    # set current station
    sid = shared.config.station_id
    if sid is not None:
        # make sure private key exists
        assert facebook.private_key_for_visa_signature(identifier=sid) is not None,\
            'failed to get sign key for current station: %s' % sid
        print('set current user: %s' % sid)
        facebook.current_user = facebook.user(identifier=sid)
    return facebook


def init_ans(shared: GlobalVariable) -> AddressNameService:
    ans = AddressNameServer()
    factory = ID.factory()
    ID.register(factory=ANSFactory(factory=factory, ans=ans))
    # load ANS records from 'config.ini'
    config = shared.config
    ans.fix(fixed=config.ans_records)
    return ans


def init_pusher(shared: GlobalVariable) -> Pusher:
    # create notification pusher
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


def init_dispatcher(shared: GlobalVariable) -> Dispatcher:
    # create dispatcher
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


# noinspection PyUnusedLocal
def stop_dispatcher(shared: GlobalVariable) -> bool:
    # TODO: stop Dispatcher
    # dispatcher = Dispatcher()
    # dispatcher.stop()
    return True


# noinspection PyUnusedLocal
def stop_pusher(shared: GlobalVariable) -> bool:
    # stop PushCenter
    center = PushCenter()
    center.stop()
    return True
