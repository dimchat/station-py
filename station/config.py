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

import dimp

from station.session import SessionServer
from station.database import Database

from station.utils import *
from station.gsp_s001 import *


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
"""

host = '127.0.0.1'
port = 9394

station_id = dimp.ID(s001_id)
station_sk = dimp.PrivateKey(s001_sk)
station_pk = station_sk.publicKey

station = Station(identifier=station_id, public_key=station_pk, host=host, port=port)
station.privateKey = station_sk

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


def load_users():
    # load moki
    user1 = dimp.User(identifier=dimp.ID(moki_id), private_key=dimp.PrivateKey(moki_sk))
    database.accounts[user1.identifier] = user1
    print('load user: ', user1)
    # load hulk
    user2 = dimp.User(identifier=dimp.ID(hulk_id), private_key=dimp.PrivateKey(hulk_sk))
    database.accounts[user2.identifier] = user2
    print('load user: ', user2)
    # load station
    database.accounts[station.identifier] = station
    print('load station: ', station)


"""
    Transceiver
    ~~~~~~~~~~~
    for pack/unpack messages
"""
transceiver = dimp.Transceiver(account=station,
                               private_key=station.privateKey,
                               barrack=database,
                               store=database)
