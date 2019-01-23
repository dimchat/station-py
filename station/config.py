# -*- coding: utf-8 -*-

"""
    Configuration
    ~~~~~~~~~~~~~

    Configure Station
"""

import dimp

from station.gsp_s001 import *
from station.session import SessionServer
from station.database import Database


class Station(dimp.Station):

    # def __init__(self, identifier: dimp.ID, public_key: dimp.PublicKey, host: str, port: int=9394):
    #     super().__init__(identifier=identifier, public_key=public_key, host=host, port=port)

    def pack(self, receiver: dimp.ID, content: dimp.Content) -> dimp.ReliableMessage:
        env = dimp.Envelope(sender=self.identifier, receiver=receiver)
        msg = dimp.InstantMessage.new(content=content, envelope=env)
        msg = transceiver.encrypt(msg)
        msg = transceiver.sign(msg)
        return msg

    def unpack(self, msg: dimp.ReliableMessage) -> dimp.Content:
        msg = transceiver.verify(msg)
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

"""
    Transceiver
    ~~~~~~~~~~~
    for pack/unpack messages
"""
transceiver = dimp.Transceiver(account=station,
                               private_key=station.privateKey,
                               barrack=database,
                               store=database)
