#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    DIM Station
    ~~~~~~~~~~~

    DIM network server node
"""

from socketserver import TCPServer, ThreadingTCPServer

from mkm.immortals import *
import dimp

from station.transceiver import barrack
from station.config import station
from station.handler import DIMRequestHandler


def load_users():

    id1 = dimp.ID(moki_id)
    sk1 = dimp.PrivateKey(moki_sk)
    user1 = dimp.User(identifier=id1, private_key=sk1)
    barrack.accounts[id1] = user1
    print('load user: ', user1)

    id2 = dimp.ID(hulk_id)
    sk2 = dimp.PrivateKey(hulk_sk)
    user2 = dimp.User(identifier=id2, private_key=sk2)
    barrack.accounts[id2] = user2
    print('load user: ', user2)


if __name__ == '__main__':

    load_users()

    # start TCP server
    TCPServer.allow_reuse_address = True
    server_address = (station.host, station.port)
    server = ThreadingTCPServer(server_address=server_address,
                                RequestHandlerClass=DIMRequestHandler)
    print(server_address, ' is listening...')
    server.serve_forever()
