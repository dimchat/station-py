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
from typing import List

from dimp import ID
from dimp import Content, TextContent
from dimp import ReliableMessage

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.client import Server, Terminal, ClientMessenger

from etc.cfg_init import g_database
from robots.config import dims_connect, g_facebook


"""
    Current Station
    ~~~~~~~~~~~~~~~
"""
# station_id = 'gsp-s001@x5Zh9ixt8ECr59XLye1y5WWfaX4fcoaaSC'
# station_id = 'gsp-india@x15NniVboopEtD3d81cbUibftcewMxzZLw'
station_id = 'gsp-yjd@wjPLYSyaZ7fe4aNL8DJAvHBNnFcgK76eYq'

# station_host = '127.0.0.1'
# station_host = '106.52.25.169'  # dimchat-gz
# station_host = '124.156.108.150'  # dimchat-hk
# station_host = '147.139.30.182'   # india
station_host = '149.129.234.145'  # yjd
station_port = 9394

station_id = ID.parse(identifier=station_id)
g_station = Server(identifier=station_id, host=station_host, port=station_port)
g_facebook.cache_user(user=g_station)


"""
    Messenger for Test
    ~~~~~~~~~~~~~~~~~~
"""


class TestMessenger(ClientMessenger):

    def process_content(self, content: Content, r_msg: ReliableMessage) -> List[Content]:
        self.info('received content: %s -> %s' % (r_msg.sender, content))
        return super().process_content(content=content, r_msg=r_msg)


g_messenger = TestMessenger()
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
    print('**** Login station: %s' % g_station)
    user = g_facebook.user(identifier=identifier)
    g_facebook.current_user = user
    dims_connect(terminal=g_client, messenger=g_messenger, server=g_station)


def logout():
    g_client.server.disconnect()


def parse_command(argv: list):
    sender = get_opt(args=argv, key='--sender')
    receiver = get_opt(args=argv, key='--receiver')
    sender = ID.parse(identifier=sender)
    receiver = ID.parse(identifier=receiver)
    if sender is None or receiver is None:
        show_help(path=argv[0])
    else:
        login(identifier=sender)
        # check receiver
        cmd = g_database.login_command(identifier=receiver)
        print('**** %s => %s' % (receiver, cmd))
        time.sleep(16)
        do_test(sender=sender, receiver=receiver)
        time.sleep(8)
        logout()


def send_text(text: str, receiver: ID):
    content = TextContent(text=text)
    g_client.messenger.send_content(sender=None, receiver=receiver, content=content)


# TODO: write test code here
def do_test(sender: ID, receiver: ID):
    print('**** Sending message: %s -> %s\n' % (sender, receiver))
    time_array = time.localtime()
    tag = time.strftime('%m-%d %H:%M:%S', time_array)
    x = 0
    while True:
        x += 1
        for y in range(1):
            text = '[%s] Test %d, %d' % (tag, x, y)
            print('**** Sending "%s" to %s' % (text, receiver))
            send_text(text=text, receiver=receiver)
        print('\n**** Sleeping...\n')
        time.sleep(5)


if __name__ == '__main__':
    print('********************************')
    parse_command(argv=sys.argv)
