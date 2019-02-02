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

import dimp

from .session import SessionServer
from .database import Database

from .utils import *
from .gsp_s001 import *


class Station(dimp.Station):

    # def __init__(self, identifier: dimp.ID, public_key: dimp.PublicKey, host: str, port: int=9394):
    #     super().__init__(identifier=identifier, public_key=public_key, host=host, port=port)

    def pack(self, receiver: dimp.ID, content: dimp.Content) -> dimp.ReliableMessage:
        env = dimp.Envelope(sender=self.identifier, receiver=receiver)
        msg = dimp.InstantMessage.new(content=content, envelope=env)
        msg = transceiver.encrypt(msg)
        msg = transceiver.sign(msg)
        return msg

    def verify(self, msg: dimp.ReliableMessage) -> dimp.SecureMessage:
        if 'meta' in msg:
            # save meta for sender
            database.save_meta(identifier=msg.envelope.sender, meta=msg.meta)
        return transceiver.verify(msg)

    def decrypt(self, msg: dimp.SecureMessage) -> dimp.Content:
        msg = msg.trim(self.identifier)
        msg = transceiver.decrypt(msg)
        content = msg.content
        return content


"""
    DIM Network Server
    ~~~~~~~~~~~~~~~~~~
    
    1. ID
    2. Private Key
    3. Host (IP)
    4. Port (9394)
"""
host = '0.0.0.0'
port = 9394

station_id = dimp.ID(s001_id)
station_sk = dimp.PrivateKey(s001_sk)
station_pk = station_sk.publicKey

station = Station(identifier=station_id, public_key=station_pk, host=host, port=port)
station.privateKey = station_sk
station.running = False


"""
    Session Server
    ~~~~~~~~~~~~~~
    for login user
"""
session_server = SessionServer()


"""
    Database
    ~~~~~~~~
    for cached messages, profile manage(Barrack), reused symmetric keys(KeyStore)
"""
database = Database()


def load_accounts():
    print('======== loading accounts')

    print('loading immortal user: ', moki_id)
    database.save_meta(identifier=dimp.ID(moki_id), meta=dimp.Meta(moki_meta))
    database.save_private_key(identifier=dimp.ID(moki_id), private_key=dimp.PrivateKey(moki_sk))

    print('loading immortal user: ', hulk_id)
    database.save_meta(identifier=dimp.ID(hulk_id), meta=dimp.Meta(hulk_meta))
    database.save_private_key(identifier=dimp.ID(hulk_id), private_key=dimp.PrivateKey(hulk_sk))

    print('loading station: ', station)
    database.accounts[station.identifier] = station

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
            meta = dimp.Meta(json_dict(data))
            identifier = meta.generate_identifier(network=dimp.NetworkID.Main)
            if identifier in database.accounts:
                # already exists
                continue
            if path.endswith(identifier.address + '/meta.js'):
                # address matched
                sk = database.load_private_key(identifier=identifier)
                if sk:
                    user = dimp.User(identifier=identifier, private_key=sk)
                    database.accounts[identifier] = user
                else:
                    account = dimp.Account(identifier=identifier, public_key=meta.key)
                    database.accounts[identifier] = account

    print('======== loaded')


"""
    Transceiver
    ~~~~~~~~~~~
    for pack/unpack messages
"""
transceiver = dimp.Transceiver(account=station,
                               private_key=station.privateKey,
                               barrack=database,
                               store=database)
