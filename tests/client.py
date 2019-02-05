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

from station.config import station, database
from station.config import load_accounts
from station.utils import *


identifier_map = {
    'moki': moki.identifier,
    'hulk': hulk.identifier,
}


def receive_handler(cli):
    incomplete_data = None
    while cli.running:
        # read data
        if incomplete_data is None:
            data = b''
        else:
            data = incomplete_data
            incomplete_data = None
        # read all data
        while cli.running:
            try:
                part = cli.sock.recv(1024)
                data += part
                if len(part) < 1024:
                    break
            except OSError:
                break
        # split package(s)
        packages = data.split(b'\n')
        count = 0
        for pack in packages:
            count += 1
            if len(pack) == 0:
                # skip empty package
                continue
            # one line(pack) one message
            line = ''
            try:
                # unwrap message package
                data = pack

                # decode message
                line = data.decode('utf-8')
                cli.receive_message(json_dict(line))
            except UnicodeDecodeError as error:
                print('decode error:', error)
            except ValueError as error:
                if len(packages) == count:
                    # partially data, push back for next input
                    print('incomplete data: %d bytes' % len(line))
                    incomplete_data = pack
                else:
                    print('value error:', error, 'line:', line)


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

    def switch_user(self, identifier: dimp.ID):
        user = database.account(identifier=identifier)
        if user:
            self.user = user
            self.trans = dimp.Transceiver(identifier=self.user.identifier,
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

    def receive_message(self, msg: dict):
        r_msg = dimp.ReliableMessage(msg)
        s_msg = self.trans.verify(r_msg)
        i_msg = self.trans.decrypt(s_msg)
        self.receive_content(sender=i_msg.envelope.sender, content=i_msg.content)

    def receive_content(self, sender: dimp.ID, content: dimp.Content):
        console.stdout.write('\r')
        if content.type == dimp.MessageType.Text:
            self.show(sender=sender, content=content)
        elif content.type == dimp.MessageType.Command:
            self.execute(sender=sender, content=content)
        else:
            print('***** Message content from "%s": %s' % (sender, content))
        # show prompt
        console.stdout.write(console.prompt)
        console.stdout.flush()

    def show(self, sender: dimp.ID, content: dimp.Content):
        print('***** Message from "%s": %s' % (sender.name, content['text']))

    def execute(self, sender: dimp.ID, content: dimp.Content):
        command = content['command']
        if 'handshake' == command:
            cmd = dimp.HandshakeCommand(content)
            # message = content['message']
            if 'DIM!' == cmd.message:
                print('##### handshake OK!')
            elif 'DIM?' == cmd.message:
                print('##### handshake again with new session key: %s' % cmd.session)
                self.session_key = cmd.session
        elif 'meta' == command:
            cmd = dimp.MetaCommand(content)
            if cmd.meta:
                print('##### received a meta for %s' % cmd.identifier)
                database.save_meta(identifier=cmd.identifier, meta=cmd.meta)
        elif 'profile' == command:
            cmd = dimp.ProfileCommand(content)
            if cmd.profile:
                print('##### received a profile for %s' % cmd.identifier)
                profile = content['profile']
                signature = content['signature']
                print('      profile: %s' % profile)
                database.save_profile(identifier=cmd.identifier, profile=profile, signature=signature)
        else:
            print('command from "%s": %s (%s)' % (sender.name, content['command'], content))


class Console(Cmd):

    prompt = '[DIM] > '
    intro = '\n\tWelcome to DIM world!\n'

    def __init__(self):
        super().__init__()
        self.receiver = None
        self.do_login(client.user.identifier)
        self.do_call('station')

    def emptyline(self):
        print('')
        print('    Usage:')
        print('        login <ID>        - switch user (must say "hello" twice after login)')
        print('        logout            - clear session')
        print('        hello             - handshake with the current station')
        print('        show users        - list online users')
        print('        search <number>   - search users by number')
        print('        profile <ID>      - query profile with ID')
        print('        call <ID>         - change receiver to another user (or "station")')
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
            cmd = dimp.HandshakeCommand.start(session=client.session_key)
            print('handshake with "%s"...' % self.receiver)
            client.send(receiver=self.receiver, content=cmd)
            self.receiver = receiver

    def do_login(self, name: str):
        if name in identifier_map:
            sender = identifier_map[name]
        elif len(name) > 30:
            sender = dimp.ID(name)
        else:
            sender = None
        if sender:
            client.switch_user(identifier=sender)
            print('login as %s' % sender)
            self.prompt = Console.prompt + sender.name + '$ '
        else:
            print('unknown user: %s' % name)

    def do_logout(self, arg):
        if client.user is None:
            print('not login yet')
        else:
            print('%s logout' % client.user.identifier)
            client.user = None
            client.session_key = None
        self.receiver = None
        self.prompt = Console.prompt

    def do_call(self, name: str):
        if client.user is None:
            print('login first')
        elif name == 'station':
            self.receiver = station.identifier
            print('talking with station(%s) now!' % self.receiver)
        elif name in identifier_map:
            self.receiver = identifier_map[name]
            print('talking with %s now!' % self.receiver)
        else:
            receiver = dimp.ID(name)
            if receiver:
                # query meta for receiver
                cmd = dimp.MetaCommand.query(identifier=receiver)
                client.send(receiver=station.identifier, content=cmd)
                # switch receiver
                self.receiver = receiver
                print('talking with %s now!' % self.receiver)
            else:
                print('unknown user: %s' % name)

    def do_send(self, msg: str):
        if client.user is None:
            print('login first')
        elif len(msg) > 0:
            content = dimp.TextContent.new(text=msg)
            client.send(receiver=self.receiver, content=content)

    def do_show(self, name: str):
        if 'users' == name:
            cmd = dimp.CommandContent.new(command='users')
            client.send(receiver=station.identifier, content=cmd)
        else:
            print('I don\'t understand.')

    def do_search(self, keywords: str):
        cmd = dimp.CommandContent.new(command='search')
        cmd['keywords'] = keywords
        client.send(receiver=station.identifier, content=cmd)

    def do_profile(self, name: str):
        profile = None
        if not name:
            identifier = client.user.identifier
        elif name == 'station':
            identifier = station.identifier
        elif name in identifier_map:
            identifier = identifier_map[name]
        elif name.find('@') > 0:
            identifier = dimp.ID(name)
        elif name.startswith('{') and name.endswith('}'):
            identifier = client.user.identifier
            profile = json_dict(name)
        else:
            print('I don\'t understand.')
            return
        if profile:
            sk = client.user.privateKey
            cmd = dimp.ProfileCommand.pack(identifier=identifier, private_key=sk, profile=profile)
        else:
            cmd = dimp.ProfileCommand.query(identifier=identifier)
        client.send(receiver=station.identifier, content=cmd)


if __name__ == '__main__':
    load_accounts()

    client = Client(identifier=moki.identifier)
    client.connect(host=station.host, port=station.port)

    console = Console()
    console.receiver = station.identifier

    console.cmdloop()
