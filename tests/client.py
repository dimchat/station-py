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

from cmd import Cmd
from typing import Optional

from startrek import DeparturePriority

from dimsdk import json_decode
from dimsdk import ID, Document
from dimsdk import TextContent
from dimsdk import BaseCommand, DocumentCommand

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Logging
from libs.client import Terminal, ClientMessenger

from robots.config import dims_connect, current_station
from robots.config import g_facebook


"""
    Messenger for Chat Bot client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger(facebook=g_facebook)
g_facebook.messenger = g_messenger


class Console(Cmd, Logging):

    prompt = '[DIM] > '
    intro = '\n\tWelcome to DIM world!\n'

    def __init__(self):
        super().__init__()
        self.client: Optional[Terminal] = None
        self.receiver = None
        self.do_call('station')

    def login(self, identifier: ID):
        # logout first
        self.logout()
        # login with user ID
        facebook = g_messenger.facebook
        user = facebook.user(identifier=identifier)
        facebook.current_user = user
        client = Terminal()
        server = current_station()
        dims_connect(terminal=client, server=server, user=user, messenger=g_messenger)
        self.client = client
        if self.receiver is None:
            self.receiver = server.identifier

    def logout(self):
        client = self.client
        if client is not None:
            client.stop()
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
            facebook = g_messenger.facebook
            user = facebook.current_user
            if self.receiver:
                print('You(%s) are talking with "%s" now.' % (user.identifier, self.receiver))
            else:
                print('%s is login in' % user.identifier)

    def do_exit(self, arg):
        client = self.client
        if client is not None:
            client.stop()
            self.client = None
        self.info(msg='Bye!')
        return True

    def do_login(self, name: str):
        sender = ID.parse(identifier=name)
        if sender is None:
            self.info('unknown user: %s' % name)
        else:
            self.info('login as %s' % sender)
            self.login(identifier=sender)
            facebook = g_messenger.facebook
            self.prompt = Console.prompt + facebook.name(identifier=sender) + '$ '

    def do_logout(self, arg):
        if self.client is None:
            self.info('not login yet')
        else:
            facebook = g_messenger.facebook
            self.info('%s logout' % facebook.current_user.identifier)
            self.logout()
        self.prompt = Console.prompt

    def do_call(self, name: str):
        if self.client is None:
            self.info('login first')
            return
        receiver = ID.parse(identifier=name)
        if receiver is None:
            self.info('unknown user: %s' % name)
        else:
            facebook = g_messenger.facebook
            meta = facebook.meta(identifier=receiver)
            self.info('talking with %s now, meta=%s' % (receiver, meta))
            # switch receiver
            self.receiver = receiver

    def do_send(self, msg: str):
        if self.client is None:
            self.info('login first')
            return
        if len(msg) > 0:
            content = TextContent.create(text=msg)
            g_messenger.send_content(sender=None, receiver=self.receiver,
                                     content=content, priority=DeparturePriority.NORMAL)

    def do_broadcast(self, msg: str):
        if self.client is None:
            self.info('login first')
            return
        if len(msg) > 0:
            content = TextContent.create(text=msg)
            self.client.broadcast_content(content=content, receiver=self.receiver)

    def do_show(self, name: str):
        if self.client is None:
            self.info('login first')
            return
        if 'users' == name:
            cmd = BaseCommand(cmd='users')
            self.client.send_command(content=cmd)
        else:
            self.info('I don\'t understand.')

    def do_search(self, keywords: str):
        if self.client is None:
            self.info('login first')
            return
        cmd = BaseCommand(cmd='search')
        cmd['keywords'] = keywords
        self.client.send_command(content=cmd)

    def do_profile(self, name: str):
        if self.client is None:
            self.info('login first')
            return
        facebook = g_messenger.facebook
        user = facebook.current_user
        profile = None
        if name is None:
            identifier = user.identifier
        elif name.startswith('{') and name.endswith('}'):
            identifier = user.identifier
            profile = json_decode(string=name)
        else:
            identifier = ID.parse(identifier=name)
            if identifier is None:
                self.info('I don\'t understand.')
                return
        if profile:
            private_key = facebook.private_key_for_signature(identifier=identifier)
            assert private_key is not None, 'failed to get private key for client: %s' % self.client
            # create new profile and set all properties
            tai = Document.create(doc_type=Document.VISA, identifier=identifier)
            for key in profile:
                tai.set_property(key, profile.get(key))
            tai.sign(private_key=private_key)
            cmd = DocumentCommand.response(identifier=identifier, document=tai)
        else:
            cmd = DocumentCommand.query(identifier=identifier)
        self.client.send_command(content=cmd)


if __name__ == '__main__':

    console = Console()
    console.cmdloop()
