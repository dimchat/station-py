#! /usr/bin/env python3
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
from dimp import TextContent
from dimp import Command, ProfileCommand

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.client import Terminal, ClientMessenger

from robots.config import open_bridge
from robots.config import g_keystore, g_facebook, g_station


"""
    Messenger for Chat Bot client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore

# current station
g_messenger.set_context('station', g_station)

g_facebook.messenger = g_messenger


class Console(Cmd):

    prompt = '[DIM] > '
    intro = '\n\tWelcome to DIM world!\n'

    def __init__(self):
        super().__init__()
        self.client: Terminal = None
        self.receiver = None
        self.do_call('station')

    @staticmethod
    def info(msg: str):
        print('\r%s' % msg)

    def login(self, identifier: ID):
        # logout first
        self.logout()
        # login with user ID
        g_facebook.current_user = g_facebook.user(identifier=identifier)
        self.info('connecting to %s ...' % g_station)
        client = Terminal()
        open_bridge(terminal=client, messenger=g_messenger, station=g_station)
        self.client = client
        if self.receiver is None:
            self.receiver = g_station.identifier

    def logout(self):
        client = self.client
        if client:
            self.info('disconnect from %s ...' % client.station)
            client.disconnect()
            self.client = None
        self.receiver = None

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
        print('        broadcast <text>  - send broadcast message')
        print('        exit              - terminate')
        print('')
        if self.client:
            if self.receiver:
                print('You(%s) are talking with "%s" now.' % (g_facebook.current_user.identifier, self.receiver))
            else:
                print('%s is login in' % g_facebook.current_user.identifier)

    def do_exit(self, arg):
        if self.client:
            self.client.disconnect()
            self.client = None
        print('Bye!')
        return True

    def do_login(self, name: str):
        sender = g_facebook.identifier(name)
        if sender is None:
            self.info('unknown user: %s' % name)
        else:
            self.info('login as %s' % sender)
            self.login(identifier=sender)
            self.prompt = Console.prompt + sender.name + '$ '

    def do_logout(self, arg):
        if self.client is None:
            self.info('not login yet')
        else:
            self.info('%s logout' % g_facebook.current_user.identifier)
            self.logout()
        self.prompt = Console.prompt

    def do_call(self, name: str):
        if self.client is None:
            self.info('login first')
            return
        receiver = g_facebook.identifier(name)
        if receiver is None:
            self.info('unknown user: %s' % name)
        else:
            meta = g_facebook.meta(identifier=receiver)
            self.info('talking with %s now, meta=%s' % (receiver, meta))
            # switch receiver
            self.receiver = receiver

    def do_send(self, msg: str):
        if self.client is None:
            self.info('login first')
            return
        if len(msg) > 0:
            content = TextContent.new(text=msg)
            self.client.messenger.send_content(content=content, receiver=self.receiver)

    def do_broadcast(self, msg: str):
        if self.client is None:
            self.info('login first')
            return
        if len(msg) > 0:
            content = TextContent.new(text=msg)
            self.client.broadcast_content(content=content, receiver=self.receiver)

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
        if name is None:
            identifier = g_facebook.current_user.identifier
        elif name.startswith('{') and name.endswith('}'):
            identifier = g_facebook.current_user.identifier
            profile = json.loads(name)
        else:
            identifier = g_facebook.identifier(name)
            if identifier is None:
                self.info('I don\'t understand.')
                return
        if profile:
            private_key = g_facebook.private_key_for_signature(identifier=g_facebook.current_user.identifier)
            assert private_key is not None, 'failed to get private key for client: %s' % self.client
            # create new profile and set all properties
            tai = Profile.new(identifier=identifier)
            for key in profile:
                tai.set_property(key, profile.get(key))
            tai.sign(private_key=private_key)
            cmd = ProfileCommand.response(identifier=identifier, profile=tai)
        else:
            cmd = ProfileCommand.query(identifier=identifier)
        self.client.send_command(cmd=cmd)


if __name__ == '__main__':

    console = Console()
    console.cmdloop()
