#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    DIM Client
    ~~~~~~~~~~

    Simple client for testing
"""

import socket
from threading import Thread

import unittest

import dimp

from mkm.immortals import *
from dkd.transform import json_str, json_dict

from station.config import station
from station.transceiver import barrack, store
from station.gsp_s001 import *


trans = dimp.Transceiver(account=moki,
                         private_key=moki.privateKey,
                         barrack=barrack,
                         store=store)


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

    id3 = dimp.ID(s001_id)
    sk3 = dimp.PrivateKey(s001_sk)
    host = '127.0.0.1'
    port = 9394
    station3 = dimp.Station(identifier=id3, public_key=sk3.publicKey, host=host, port=port)
    barrack.accounts[id3] = station3
    print('load station: ', station3)


class Common:

    host: str = '127.0.0.1'
    port: int = 9394
    sock: socket = None

    user: dimp.User = None


def send_message():
    pass


def handle_message(data):
    if len(data) == 0:
        return
    msg = json_dict(data)
    print('received msg: ', msg)
    msg = dimp.ReliableMessage(msg)
    msg = trans.verify(msg)
    msg = trans.decrypt(msg)
    print('content: ', msg.content)


def receive():
    data = b''
    while True:
        part = Common.sock.recv(1024)
        data += part
        if len(part) < 1024:
            break
    return data


def receive_message():
    while True:
        data = receive()
        handle_message(data)


class ClientTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print('\n================ %s' % cls)

        server_address = (Common.host, Common.port)

        Common.sock = socket.socket()
        Common.sock.connect(server_address)
        print('connect to', server_address)

        thread1 = Thread(target=receive_message)
        thread1.start()

    @classmethod
    def tearDownClass(cls):
        print('\n================ %s' % cls)

        Common.sock.close()
        print('socket closed')

    def test1_identifier(self):
        print('\n---------------- %s' % self)

        # user
        id1 = dimp.ID(moki_id)
        sk1 = dimp.PrivateKey(moki_sk)
        Common.user = dimp.User(identifier=id1, private_key=sk1)
        print('user: ', Common.user)

    def test2_login(self):
        print('\n---------------- %s' % self)

        pass

    def test3_send(self):
        print('\n---------------- %s' % self)

        sender = Common.user.identifier
        receiver = station.identifier

        password = dimp.SymmetricKey.generate({'algorithm': 'AES'})

        while True:
            data = input('[DIM] Type message: ')
            if len(data) == 0:
                print('Input nothing, terminated.')
                break

            if data == '1':
                account: dimp.Account = barrack.accounts[hulk_id]
                receiver = account.identifier
                print('change receiver: ', receiver)
                continue
            elif data == '0':
                receiver = station.identifier
                print('change receiver: ', receiver)
                continue

            # Message
            content = dimp.TextContent.new(text=data)
            i_msg = dimp.InstantMessage.new(content=content, sender=sender, receiver=receiver)
            s_msg = i_msg.encrypt(password=password, public_key=station.publicKey)
            r_msg = s_msg.sign(private_key=Common.user.privateKey)

            # Send
            Common.sock.sendall(json_str(r_msg).encode('utf-8'))


if __name__ == '__main__':

    load_users()

    unittest.main()
