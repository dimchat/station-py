#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    DIM Client
    ~~~~~~~~~~

    Simple client for testing
"""

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

import socket
from threading import Thread

import dimp

from mkm.immortals import *
from dkd.transform import json_str, json_dict

from station.config import station
from station.transceiver import barrack, store


name_list = {
    'moki': {'ID': moki_id, 'SK': moki_sk},
    'hulk': {'ID': hulk_id, 'SK': hulk_sk},
}


def load_users():

    # loading
    for key in name_list:
        item = name_list[key]
        id1 = dimp.ID(item['ID'])
        sk1 = dimp.PrivateKey(item['SK'])
        user = dimp.User(identifier=id1, private_key=sk1)
        barrack.accounts[id1] = user
        print('load user: ', user)

    # add station as an account
    barrack.accounts[station.identifier] = station
    print('load station: ', station)


def receive_handler(cli):
    while cli.running:
        # read data
        data = b''
        while cli.running:
            part = cli.sock.recv(1024)
            data += part
            if len(part) < 1024:
                break
        if len(data) == 0:
            continue
        # split message(s)
        array = data.decode('utf-8').splitlines()
        for msg in array:
            cli.receive_data(msg)


def send_handler(cli):
    pass


class Client:

    def __init__(self, identifier: dimp.ID):
        super().__init__()
        self.user = None
        self.trans = None
        self.switch_user(identifier=identifier)
        # socket
        self.sock = None
        self.thread_receive = None
        self.thread_send = None
        self.running = False

    def switch_user(self, identifier: dimp.ID):
        if identifier in barrack.accounts:
            self.user = barrack.accounts[identifier]
            self.trans = dimp.Transceiver(account=self.user,
                                          private_key=self.user.privateKey,
                                          barrack=barrack,
                                          store=store)
        else:
            raise LookupError('User not found: ' + identifier)

    def connect(self, host: str, port: int=9394):
        if self.sock:
            self.sock.close()
        # connect to new socket (host:port)
        address = (host, port)
        self.sock = socket.socket()
        self.sock.connect(address)
        # start threads
        self.running = True
        if self.thread_receive is None:
            self.thread_receive = Thread(target=receive_handler, args=(self,))
            self.thread_receive.start()
        if self.thread_send is None:
            self.thread_send = Thread(target=send_handler, args=(self,))
            self.thread_send.start()

    def close(self):
        # stop thread
        self.running = False
        if self.thread_send:
            self.thread_send = None
        if self.thread_receive:
            self.thread_receive = None
        # disconnect the socket
        if self.sock:
            self.sock.close()

    def send(self, receiver: dimp.ID, content: dimp.Content):
        account = barrack.account(receiver)
        if account is None:
            raise LookupError('Receiver not found: ' + receiver)
        sender = self.user.identifier
        password = store.symmetric_key(receiver=receiver)
        # packing message
        i_msg = dimp.InstantMessage.new(content=content, sender=sender, receiver=receiver)
        s_msg = i_msg.encrypt(password=password, public_key=account.publicKey)
        r_msg = s_msg.sign(private_key=self.user.privateKey)
        # send out message
        self.sock.sendall(json_str(r_msg).encode('utf-8'))

    def receive_data(self, data: str):
        data = json_dict(data)
        msg = dimp.ReliableMessage(data)
        msg = self.trans.verify(msg)
        msg = self.trans.decrypt(msg)
        self.receive(sender=msg.envelope.sender, content=msg.content)

    def receive(self, sender: dimp.ID, content: dimp.Content):
        print('received from %s: %s' % (sender, content))
        if content.type == dimp.MessageType.Text:
            print('**** Text: %s ****' % content['text'])
        elif content.type == dimp.MessageType.Command:
            print('**** Command: %s, Message: %s ****' % (content['command'], content['message']))


def console(receiver: dimp.ID):

    while True:

        data = input('[DIM] Type message: ')
        if len(data) == 0:
            print('Input nothing, terminated.')
            break

        if data == 'send to station':
            receiver = station.identifier
            print('send to: %s' % receiver)
            continue
        elif data == 'send to moki':
            receiver = moki_id
            print('send to: %s' % receiver)
            continue
        elif data == 'send to hulk':
            receiver = hulk_id
            print('send to: %s' % receiver)
            continue
        elif data == 'login moki':
            sender = name_list['moki']['ID']
            client.switch_user(identifier=sender)
            print('login: %s' % sender)
            continue
        elif data == 'login hulk':
            sender = name_list['hulk']['ID']
            client.switch_user(identifier=sender)
            print('login: %s' % sender)
            continue

        # Message
        content = dimp.TextContent.new(text=data)
        client.send(receiver=receiver, content=content)


if __name__ == '__main__':

    load_users()

    client = Client(identifier=moki_id)
    client.connect(host=station.host, port=station.port)

    console(receiver=hulk_id)
