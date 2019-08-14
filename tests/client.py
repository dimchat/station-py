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

import json
from cmd import Cmd

import socket
from threading import Thread

import sys
import os

from dkd import Envelope

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from dimp import ID, Profile
from dimp import ContentType, Content, Command, TextContent
from dimp import InstantMessage, ReliableMessage
from dimp import HandshakeCommand, MetaCommand, ProfileCommand

from common import base64_encode, Log
from common import facebook, keystore, messanger, database, load_accounts
from common import s001, s001_port
from common import moki, hulk


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
station = s001

remote_host = '127.0.0.1'
# remote_host = '124.156.108.150'  # dimchat.hk
# remote_host = '134.175.87.98'  # dimchat.gz
remote_port = s001_port

database.base_dir = '/tmp/.dim/'

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
                cli.receive_message(json.loads(line))
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

    def __init__(self, identifier: ID):
        super().__init__()
        self.user = None
        self.switch_user(identifier=identifier)
        # socket
        self.sock = None
        self.thread_receive = None
        self.running = False
        # session
        self.session_key = None

    def switch_user(self, identifier: ID):
        user = facebook.user(identifier=identifier)
        if user:
            self.user = user
            keystore.user = user
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

    def send(self, receiver: ID, content: Content):
        sender = self.user.identifier
        # packing message
        i_msg = InstantMessage.new(content=content, sender=sender, receiver=receiver)
        r_msg = messanger.encrypt_sign(i_msg)
        # send out message
        pack = json.dumps(r_msg) + '\n'
        self.sock.sendall(pack.encode('utf-8'))

    def receive_message(self, msg: dict):
        r_msg = ReliableMessage(msg)
        i_msg = messanger.verify_decrypt(r_msg)
        self.receive_content(envelope=i_msg.envelope, content=i_msg.content)

    def receive_content(self, content: Content, envelope: Envelope):
        sender = ID(envelope.sender)
        when = Log.time_string(envelope.time)
        console.stdout.write('\r')
        if content.type == ContentType.Text:
            self.show(envelope=envelope, content=content)
        elif content.type == ContentType.Command:
            self.execute(envelope=envelope, content=content)
        else:
            print('[%s] ***** Message content from "%s": %s' % (when, sender, content))
        # show prompt
        console.stdout.write(console.prompt)
        console.stdout.flush()

    def show(self, envelope: Envelope, content: Content):
        sender = ID(envelope.sender)
        when = Log.time_string(envelope.time)
        print('[%s] ***** Message from "%s": %s' % (when, sender.name, content['text']))

    def execute(self, envelope: Envelope, content: Content):
        sender = ID(envelope.sender)
        when = Log.time_string(envelope.time)
        command = content['command']
        if 'handshake' == command:
            cmd = HandshakeCommand(content)
            message = cmd.message
            if 'DIM!' == message:
                print('##### handshake OK!')
            elif 'DIM?' == message:
                session = cmd.session
                print('##### handshake again with new session key: %s' % session)
                self.session_key = session
        elif 'meta' == command:
            cmd = MetaCommand(content)
            identifier = cmd.identifier
            meta = cmd.meta
            if meta:
                print('##### received a meta for %s' % identifier)
                database.save_meta(identifier=identifier, meta=meta)
        elif 'profile' == command:
            cmd = ProfileCommand(content)
            identifier = cmd.identifier
            profile = cmd.profile
            if profile:
                print('##### received a profile for %s' % identifier)
                database.save_profile(profile=profile)
        elif 'search' == command:
            print('##### received search response')
            if 'users' in content:
                users = content['users']
                print('      users:', json.dumps(users))
            if 'results' in content:
                results = content['results']
                print('      results:', json.dumps(results))
        else:
            print('[%s] ***** command from "%s": %s (%s)' % (when, sender.name, content['command'], content))


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
            cmd = HandshakeCommand.start(session=client.session_key)
            print('handshake with "%s"...' % self.receiver)
            client.send(receiver=self.receiver, content=cmd)
            self.receiver = receiver

    def do_login(self, name: str):
        if name in identifier_map:
            sender = identifier_map[name]
        elif len(name) > 30:
            sender = ID(name)
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
            receiver = ID(name)
            if receiver:
                # query meta for receiver
                cmd = MetaCommand.query(identifier=receiver)
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
            content = TextContent.new(text=msg)
            client.send(receiver=self.receiver, content=content)

    def do_show(self, name: str):
        if 'users' == name:
            cmd = Command.new(command='users')
            client.send(receiver=station.identifier, content=cmd)
        else:
            print('I don\'t understand.')

    def do_search(self, keywords: str):
        cmd = Command.new(command='search')
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
            identifier = ID(name)
        elif name.startswith('{') and name.endswith('}'):
            identifier = client.user.identifier
            profile = json.loads(name)
        else:
            print('I don\'t understand.')
            return
        if profile:
            sk = client.user.privateKey
            sig = sk.sign(profile.encode('utf-8'))
            profile = {
                'ID': identifier,
                'data': profile,
                'signature': base64_encode(sig),
            }
            cmd = ProfileCommand.response(identifier=identifier, profile=Profile(profile))
        else:
            cmd = ProfileCommand.query(identifier=identifier)
        client.send(receiver=station.identifier, content=cmd)


if __name__ == '__main__':
    load_accounts(facebook=facebook)

    print('connecting to %s:%d ...' % (remote_host, remote_port))
    client = Client(identifier=moki.identifier)
    client.connect(host=remote_host, port=remote_port)

    console = Console()
    console.receiver = station.identifier

    console.cmdloop()
