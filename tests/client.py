#! /usr/bin/env python
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
    DIM Client
    ~~~~~~~~~~

    Simple client for testing
"""

from cmd import Cmd

import socket
from threading import Thread

import dimp

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from station.config import station, database, load_users
from station.utils import *


identifier_map = {
    'moki': moki.identifier,
    'hulk': hulk.identifier,
}


def receive_handler(cli):
    while cli.running:
        # read data
        data = b''
        part = b''
        while cli.running:
            try:
                part = cli.sock.recv(1024)
            finally:
                data += part
                if len(part) < 1024:
                    break
        # split message(s)
        if len(data) > 0:
            array = data.decode('utf-8').splitlines()
            for msg in array:
                cli.receive_data(msg)


class Client:

    def __init__(self, identifier: dimp.ID):
        super().__init__()
        self.user = None
        self.trans = None
        self.switch_user(identifier=identifier)
        # socket
        self.sock = None
        self.thread_receive = None
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

    def close(self):
        # stop thread
        self.running = False
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
            print('\r***** Message content from "%s": %s' % (sender, content))
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
            receiver = self.receiver
            self.receiver = station.identifier
            command = dimp.handshake_start_command(session=client.session_key)
            print('handshake with "%s": %s' % (self.receiver, command))
            client.send(receiver=self.receiver, content=command)
            self.receiver = receiver

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
