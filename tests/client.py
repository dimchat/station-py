#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""
    DIM Client
    ~~~~~~~~~~

    Simple client for testing
"""

import sys
import os

from cmd import Cmd

import socket
from threading import Thread

import dimp

from mkm.immortals import *
from dkd.transform import json_str, json_dict

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from station.config import station, database


identifier_map = {
    'moki': moki.identifier,
    'hulk': hulk.identifier,
}


def load_users():

    # loading
    id1 = dimp.ID(moki_id)
    sk1 = dimp.PrivateKey(moki_sk)
    user1 = dimp.User(identifier=id1, private_key=sk1)
    database.accounts[id1] = user1
    print('load user: ', user1)

    id2 = dimp.ID(hulk_id)
    sk2 = dimp.PrivateKey(hulk_sk)
    user2 = dimp.User(identifier=id2, private_key=sk2)
    database.accounts[id2] = user2
    print('load user: ', user2)

    # add station as an account
    database.accounts[station.identifier] = station
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
    # print('---------------- %s' % cli)
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
        # session
        self.session_key = None
        self.handshake = False

    def switch_user(self, identifier: dimp.ID):
        if identifier in database.accounts:
            self.user = database.accounts[identifier]
            self.trans = dimp.Transceiver(account=self.user,
                                          private_key=self.user.privateKey,
                                          barrack=database,
                                          store=database)
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
        account = database.account(receiver)
        if account is None:
            raise LookupError('Receiver not found: ' + receiver)
        sender = self.user.identifier
        password = database.symmetric_key(receiver=receiver)
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
        if content.type == dimp.MessageType.Text:
            self.show(sender=sender, content=content)
        elif content.type == dimp.MessageType.Command:
            self.execute(sender=sender, content=content)
        else:
            print('\r***** Received from "%s": %s' % (sender, content))
        # show prompt
        console.stdout.write(console.prompt)
        console.stdout.flush()

    def show(self, sender: dimp.ID, content: dimp.Content):
        print('\r***** Message from "%s": %s' % (sender.name, content['text']))

    def execute(self, sender: dimp.ID, content: dimp.Content):
        print('\r***** Command from "%s": %s (%s)' % (sender.name, content['command'], content))
        if 'handshake' == content['command']:
            if 'DIM?' == content['message']:
                self.session_key = content['session']
                print('      handshake again with new session key: %s' % self.session_key)
            elif 'DIM!' == content['message']:
                self.handshake = True
                print('      handshake OK!')


class Console(Cmd):

    prompt = '[DIM] > '
    intro = 'Welcome to DIM world!'

    def __init__(self):
        super().__init__()
        self.receiver = None

    def emptyline(self):
        print('')
        print('    Usage:')
        print('        login <username>  - switch user')
        print('        logout            - clear session')
        print('        hello             - handshake with station')
        print('        call <username>   - change receiver to another user or "station"')
        print('        send <text>       - send message')
        print('        exit              - terminate')
        print('')
        if client.user:
            if self.receiver:
                print('You(%s) are talking with "%s" now.' % (client.user.identifier, self.receiver))
            else:
                print('%s is login in' % client.user.identifier)

    def do_exit(self, arg):
        client.close()
        print('Bye!')
        return True

    def do_hello(self, arg):
        if client.user is None:
            print('login first')
        else:
            command = dimp.handshake_start_command(session=client.session_key)
            print('handshake with "%s": %s' % (self.receiver, command))
            client.send(receiver=self.receiver, content=command)

    def do_login(self, name: str):
        if name in identifier_map:
            sender = identifier_map[name]
            client.switch_user(identifier=sender)
            print('login as %s' % sender)
        else:
            print('unknown user: %s' % name)

    def do_logout(self, arg):
        if client.user is None:
            print('not login yet')
        else:
            print('%s logout' % client.user.identifier)
            client.user = None
            client.session_key = None

    def do_call(self, name: str):
        if client.user is None:
            print('login first')
        elif name == 'station':
            self.receiver = station.identifier
            print('talking with station (%s)' % self.receiver)
        elif name in identifier_map:
            self.receiver = identifier_map[name]
            print('talking with %s' % self.receiver)
        else:
            print('unknown user: %s' % name)

    def do_send(self, msg: str):
        if client.user is None:
            print('login first')
        elif len(msg) > 0:
            content = dimp.TextContent.new(text=msg)
            client.send(receiver=self.receiver, content=content)


if __name__ == '__main__':

    load_users()

    client = Client(identifier=moki.identifier)
    client.connect(host=station.host, port=station.port)

    console = Console()
    console.receiver = station.identifier

    console.cmdloop()
