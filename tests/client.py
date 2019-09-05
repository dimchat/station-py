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

from dimp import ID, Profile
from dimp import Content, TextContent
from dimp import Command, ProfileCommand

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from common import base64_encode
from common import g_facebook, g_database, g_messenger, load_accounts
from common import s001, s001_port
from common import moki, hulk

from robot import Robot


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
g_station = s001

g_station.host = '127.0.0.1'
# g_station.host = '124.156.108.150'  # dimchat.hk
# g_station.host = '134.175.87.98'  # dimchat.gz
g_station.port = s001_port

g_database.base_dir = '/tmp/.dim/'

identifier_map = {
    'moki': moki.identifier,
    'hulk': hulk.identifier,
}


class Client(Robot):

    def receive_command(self, cmd: Command, sender: ID) -> bool:
        if super().receive_command(cmd=cmd, sender=sender):
            return True
        command = cmd.command
        if 'search' == command:
            self.info('##### received search response')
            if 'users' in cmd:
                users = cmd['users']
                print('      users:', json.dumps(users))
            if 'results' in cmd:
                results = cmd['results']
                print('      results:', results)
        elif 'users' == command:
            self.info('##### online users: %s' % cmd.get('message'))
            if 'users' in cmd:
                users = cmd['users']
                print('      users:', json.dumps(users))
        else:
            self.info('***** command from "%s": %s (%s)' % (sender.name, cmd['command'], cmd))

    def receive_content(self, content: Content, sender: ID) -> bool:
        if super().receive_content(content=content, sender=sender):
            return True
        self.info('***** Message from "%s": %s' % (sender.name, content['text']))


class Console(Cmd):

    prompt = '[DIM] > '
    intro = '\n\tWelcome to DIM world!\n'

    def __init__(self):
        super().__init__()
        self.client: Client = None
        self.receiver = None
        self.do_call('station')

    def info(self, msg: str):
        print('\r%s' % msg)

    def login(self, identifier: ID):
        self.info('connected to %s ...' % g_station)
        client = Client(identifier=identifier)
        client.messenger = g_messenger
        client.facebook = g_facebook
        client.connect(station=g_station)
        self.client = client

    def emptyline(self):
        print('')
        print('    Usage:')
        print('        login <ID>        - switch user (must say "hello" twice after login)')
        print('        logout            - clear session')
        print('        show users        - list online users')
        print('        search <number>   - search users by number')
        print('        profile <ID>      - query profile with ID')
        print('        call <ID>         - change receiver to another user (or "station")')
        print('        send <text>       - send message')
        print('        exit              - terminate')
        print('')
        if self.client:
            if self.receiver:
                print('You(%s) are talking with "%s" now.' % (self.client.identifier, self.receiver))
            else:
                print('%s is login in' % self.client.identifier)

    def do_exit(self, arg):
        if self.client:
            self.client.disconnect()
            self.client = None
        print('Bye!')
        return True

    def do_login(self, name: str):
        if name in identifier_map:
            sender = identifier_map[name]
        elif len(name) > 30:
            sender = g_facebook.identifier(name)
        else:
            sender = None
        if sender:
            self.info('login as %s' % sender)
            self.login(identifier=sender)
            self.prompt = Console.prompt + sender.name + '$ '
        else:
            self.info('unknown user: %s' % name)

    def do_logout(self, arg):
        if self.client is None:
            self.info('not login yet')
        else:
            self.info('%s logout' % self.client.identifier)
            self.client = None
        self.receiver = None
        self.prompt = Console.prompt

    def do_call(self, name: str):
        if self.client is None:
            self.info('login first')
            return
        if name == 'station':
            self.receiver = g_station.identifier
            self.info('talking with station(%s) now!' % self.receiver)
        elif name in identifier_map:
            self.receiver = identifier_map[name]
            self.info('talking with %s now!' % self.receiver)
        else:
            receiver = g_facebook.identifier(name)
            if receiver:
                self.client.check_meta(identifier=receiver)
                # switch receiver
                self.receiver = receiver
                self.info('talking with %s now!' % self.receiver)
            else:
                self.info('unknown user: %s' % name)

    def do_send(self, msg: str):
        if self.client is None:
            self.info('login first')
            return
        if len(msg) > 0:
            content = TextContent.new(text=msg)
            self.client.send_content(content=content, receiver=self.receiver)

    def do_show(self, name: str):
        if self.client is None:
            self.info('login first')
            return
        if 'users' == name:
            cmd: Command = Command.new(command='users')
            self.client.send_command(cmd=cmd)
        else:
            self.info('I don\'t understand.')

    def do_search(self, keywords: str):
        if self.client is None:
            self.info('login first')
            return
        cmd: Command = Command.new(command='search')
        cmd['keywords'] = keywords
        self.client.send_command(cmd=cmd)

    def do_profile(self, name: str):
        if self.client is None:
            self.info('login first')
            return
        profile = None
        if not name:
            identifier = self.client.identifier
        elif name == 'station':
            identifier = g_station.identifier
        elif name in identifier_map:
            identifier = identifier_map[name]
        elif name.find('@') > 0:
            identifier = g_facebook.identifier(name)
        elif name.startswith('{') and name.endswith('}'):
            identifier = self.client.identifier
            profile = json.loads(name)
        else:
            self.info('I don\'t understand.')
            return
        if profile:
            sig = self.client.sign(profile.encode('utf-8'))
            profile = {
                'ID': identifier,
                'data': profile,
                'signature': base64_encode(sig),
            }
            cmd = ProfileCommand.response(identifier=identifier, profile=Profile(profile))
        else:
            cmd = ProfileCommand.query(identifier=identifier)
        self.client.send_command(cmd=cmd)


if __name__ == '__main__':
    load_accounts(facebook=g_facebook)

    console = Console()
    console.receiver = g_station.identifier

    console.cmdloop()
