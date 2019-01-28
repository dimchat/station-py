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

    print('======== loaded')


def process_meta_command(content: dimp.Content) -> dimp.Content:
    cmd = dimp.MetaCommand(content)
    identifier = cmd.identifier
    meta = cmd.meta
    if meta:
        # received a meta for ID
        if database.save_meta(identifier=identifier, meta=meta):
            # meta saved
            command = dimp.CommandContent.new(command='receipt')
            command['message'] = 'Meta for %s received!' % identifier
            return command
        else:
            # meta not match
            return dimp.TextContent.new(text='Meta not match %s!' % identifier)
    else:
        # querying meta for ID
        meta = database.load_meta(identifier=identifier)
        if meta:
            return dimp.MetaCommand.response(identifier=identifier, meta=meta)
        else:
            return dimp.TextContent.new(text='Sorry, meta for %s not found.' % identifier)


def process_users_command():
    sessions = session_server.sessions.copy()
    users = [identifier for identifier in sessions if sessions[identifier].request_handler]
    count = len(users)
    response = dimp.CommandContent.new(command='users')
    response['message'] = '%d user(s) connected' % count
    if count > 0:
        response['users'] = users
    return response


"""
    Transceiver
    ~~~~~~~~~~~
    for pack/unpack messages
"""
transceiver = dimp.Transceiver(account=station,
                               private_key=station.privateKey,
                               barrack=database,
                               store=database)
