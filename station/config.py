# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2019 Albert Moky
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
    Configuration
    ~~~~~~~~~~~~~

    Configure Station
"""

import os
import json

import dimp

from .database import Database
from .session import SessionServer
from .receptionist import Receptionist
from .dispatcher import Dispatcher
from .apns import ApplePushNotificationService

from .utils import *
from .gsp_s001 import s001_id, s001_sk, s001_meta

# gsp station-001
station_id = dimp.ID(s001_id)
station_sk = dimp.PrivateKey(s001_sk)
station_meta = dimp.Meta(s001_meta)


class Station(dimp.Station):

    def __init__(self, identifier: dimp.ID, host: str, port: int=9394):
        super().__init__(identifier=identifier, host=host, port=port)
        self.transceiver: dimp.Transceiver = None
        self.running = False

    def pack(self, receiver: dimp.ID, content: dimp.Content) -> dimp.ReliableMessage:
        """ Pack message from this station """
        env = dimp.Envelope(sender=self.identifier, receiver=receiver)
        i_msg = dimp.InstantMessage.new(content=content, envelope=env)
        r_msg = self.transceiver.encrypt_sign(i_msg)
        return r_msg

    def verify(self, msg: dimp.ReliableMessage) -> dimp.SecureMessage:
        # check meta (first contact?)
        meta = msg.meta
        if meta is not None:
            meta = dimp.Meta(meta)
            identifier = dimp.ID(msg.envelope.sender)
            # save meta for sender
            self.delegate.cache_meta(identifier=identifier, meta=meta)
        # message delegate
        if msg.delegate is None:
            msg.delegate = self.transceiver
        return msg.verify()

    def decrypt(self, msg: dimp.SecureMessage) -> dimp.Content:
        """ Decrypt message for this station """
        s_msg = msg.trim(self.identifier)
        s_msg.delegate = self.transceiver
        i_msg = s_msg.decrypt()
        content = i_msg.content
        return content


"""
    Database
    ~~~~~~~~
    
    for cached messages, profile manage(Barrack), reused symmetric keys(KeyStore)
"""
database = Database()
# database.base_dir = '/data/.dim/'


"""
    Session Server
    ~~~~~~~~~~~~~~

    for login user
"""
session_server = SessionServer()


"""
    Transceiver
    ~~~~~~~~~~~

    for pack/unpack messages
"""
transceiver = dimp.Transceiver(identifier=station_id,
                               private_key=station_sk,
                               barrack=database,
                               key_store=database)


"""
    DIM Network Server
    ~~~~~~~~~~~~~~~~~~

    1. ID
    2. Private Key
    3. Host (IP)
    4. Port (9394)
"""
station_host = '0.0.0.0'
station_port = 9394

remote_host = '127.0.0.1'
# remote_host = '124.156.108.150'  # dim.chat
remote_port = station_port

station = Station(identifier=station_id, host=station_host, port=station_port)
station.privateKey = station_sk
station.delegate = database
station.transceiver = transceiver
station.running = False


"""
    Apple Push Notification service (APNs)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    A service for pushing notification to offline device
"""
apns = ApplePushNotificationService(database.base_dir + 'private/apns.pem', use_sandbox=True)
apns.delegate = database


"""
    Station Receptionist
    ~~~~~~~~~~~~~~~~~~~~

    A message scanner for new guests who have just come in.
"""
receptionist = Receptionist()
receptionist.database = database
receptionist.session_server = session_server
receptionist.station = station
receptionist.apns = apns


"""
    Message Dispatcher
    ~~~~~~~~~~~~~~~~~~

    A dispatcher to decide which way to deliver message.
"""
dispatcher = Dispatcher()
dispatcher.session_server = session_server
dispatcher.database = database
dispatcher.apns = apns


def load_accounts():
    print('======== loading accounts')

    print('loading immortal user: ', moki_id)
    database.cache_meta(identifier=dimp.ID(moki_id), meta=dimp.Meta(moki_meta))
    database.cache_private_key(identifier=dimp.ID(moki_id), private_key=dimp.PrivateKey(moki_sk))

    print('loading immortal user: ', hulk_id)
    database.cache_meta(identifier=dimp.ID(hulk_id), meta=dimp.Meta(hulk_meta))
    database.cache_private_key(identifier=dimp.ID(hulk_id), private_key=dimp.PrivateKey(hulk_sk))

    print('loading station: ', station_id)
    database.cache_meta(identifier=station_id, meta=station_meta)
    database.cache_private_key(identifier=station_id, private_key=station_sk)
    database.cache_account(station)

    # scan all metas
    directory = database.base_dir + 'public'
    # get all files in messages directory and sort by filename
    files = sorted(os.listdir(directory))
    for filename in files:
        path = directory + '/' + filename + '/meta.js'
        if os.path.exists(path):
            print('loading %s' % path)
            with open(path, 'r') as file:
                data = file.read()
                # no need to check meta again
            meta = dimp.Meta(json.loads(data))
            identifier = meta.generate_identifier(network=dimp.NetworkID.Main)
            if database.account(identifier=identifier):
                # already exists
                continue
            if path.endswith(identifier.address + '/meta.js'):
                # address matched
                sk = database.private_key(identifier=identifier)
                if sk:
                    user = dimp.User(identifier=identifier, private_key=sk)
                    # database.accounts[identifier] = user
                    database.cache_account(user)
                else:
                    account = dimp.Account(identifier=identifier)
                    # database.accounts[identifier] = account
                    database.cache_account(account)

    print('======== loaded')
