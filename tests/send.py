#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2021 Albert Moky
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

import os
import sys
import time

from mkm import ID
from dimp import TextContent

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.client import Terminal, ClientMessenger
from robots.config import dims_connect, g_station


"""
    Messenger for Chat Bot client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()

g_facebook = g_messenger.facebook

g_client = Terminal()


def get_opt(args: list, key: str):
    pos = len(args) - 1
    while pos >= 0:
        item: str = args[pos]
        if item == key:
            return args[pos + 1]
        if item.startswith('%s=' % key):
            return item[len(key)+1:]
        pos -= 1


def show_help(path):
    print('\n    Usages:'
          '\n        %s [options]'
          '\n'
          '\n    Options:'
          '\n        --sender                Sender ID'
          '\n        --receiver              Receiver ID'
          '\n        --help                  Show help for commands.'
          '\n\n' % path)


def login(identifier: ID):
    user = g_facebook.user(identifier=identifier)
    g_facebook.current_user = user
    dims_connect(terminal=g_client, messenger=g_messenger, server=g_station)


def logout():
    g_client.server.disconnect()


def send_text(text: str, receiver: ID):
    content = TextContent(text=text)
    g_client.messenger.send_content(sender=None, receiver=receiver, content=content)


# TODO: write test code here
def do_test(sender: ID, receiver: ID):
    print('\n\n**** Sending message: %s -> %s\n' % (sender, receiver))
    for x in range(2):
        for y in range(10):
            text = 'Hello %d, %d' % (x, y)
            print('**** Sending "%s" to %s\n' % (text, receiver))
            send_text(text=text, receiver=receiver)
        print('**** Sleeping...\n')
        time.sleep(5)


def parse_command(argv: list):
    sender = get_opt(args=argv, key='--sender')
    receiver = get_opt(args=argv, key='--receiver')
    sender = ID.parse(identifier=sender)
    receiver = ID.parse(identifier=receiver)
    if sender is None or receiver is None:
        show_help(path=argv[0])
    else:
        login(identifier=sender)
        time.sleep(2)
        do_test(sender=sender, receiver=receiver)
        time.sleep(5)
        logout()


if __name__ == '__main__':
    parse_command(argv=sys.argv)
