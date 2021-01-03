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
    Chat bot: 'XiaoXiao'
    ~~~~~~~~~~~~~~~~~~~~

    Chat bot powered by XiaoI
"""

import sys
import os
import threading
import time

from dimp import NetworkType, Group
from dimp import TextContent

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.common import Log, Storage

from libs.client import Terminal, ClientMessenger
from libs.client import GroupManager

from robots.config import g_facebook, g_keystore, g_database, g_station
from robots.config import group_naruto
from robots.config import dims_connect
from robots.config import chat_bot, xiaoxiao_id

from etc.cfg_loader import load_user
from etc.cfg_bots import freshmen_file


"""
    Messenger for Chat Bot client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore
g_messenger.context['database'] = g_database
# chat bot
g_messenger.context['bots'] = [chat_bot('xiaoi')]

g_facebook.messenger = g_messenger


def load_freshmen() -> list:
    freshmen = []
    text = Storage.read_text(path=freshmen_file)
    if text is None:
        return freshmen
    array = text.splitlines()
    for item in array:
        identifier = g_facebook.identifier(item)
        if identifier is None:
            Log.error('ID error: %s' % item)
        elif identifier.type == NetworkType.MAIN.value:
            freshmen.append(identifier)
        else:
            # Log.error('Not a user ID: %s' % identifier)
            pass
    return freshmen


class FreshmenScanner(threading.Thread):

    def __init__(self, messenger: ClientMessenger):
        super().__init__()
        # delegate for send message
        self.messenger = messenger
        # group
        gid = g_facebook.identifier(group_naruto)
        self.__group: Group = g_facebook.group(gid)

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def __members(self) -> list:
        members = self.__group.members
        if members is None:
            return []
        self.info('got %d member(s) in group: %s' % (len(members), self.__group))
        return members

    def __freshmen(self) -> list:
        freshmen = load_freshmen()
        if freshmen is None:
            return []
        # remove existed members
        members = self.__members()
        for item in members:
            if item in freshmen:
                freshmen.remove(item)
        users = []
        for item in freshmen:
            profile = g_facebook.profile(identifier=item)
            if profile is None:
                # profile not found
                continue
            if 'data' not in profile:
                # profile empty
                continue
            # profile OK
            users.append(item)
        self.info('got freshmen: %d from %d' % (len(users), len(freshmen)))
        return users

    def __welcome(self, freshmen: list) -> TextContent:
        names = [g_facebook.nickname(item) for item in freshmen]
        count = len(names)
        if count == 1:
            string = names[0]
            msg = 'Welcome new member~ %s.' % string
        elif count > 1:
            string = ', '.join(names)
            msg = 'Welcome new members~ %s.' % string
        else:
            # should not be here
            msg = 'Welcome!'
        text = TextContent(text=msg)
        text.group = self.__group.identifier
        return text

    def __run_unsafe(self):
        #
        #  1. get freshmen and group members
        #
        freshmen = self.__freshmen()
        if len(freshmen) == 0:
            time.sleep(30)
            return
        self.info('freshmen: %s' % freshmen)
        #
        #  2. send group command for inviting freshmen
        #
        gid = self.__group.identifier
        gm = GroupManager(gid)
        gm.messenger = self.messenger
        gm.invite(freshmen)
        #
        #  3. send Welcome!
        #
        text = self.__welcome(freshmen=freshmen)
        gm.send(content=text)
        self.info('Welcome sent to %s: %s' % (gid, text))

    def run(self):
        while True:
            time.sleep(30)
            self.info('try to scan freshmen ...')
            try:
                self.__run_unsafe()
            except Exception as error:
                self.error('scan freshmen error: %s' % error)


if __name__ == '__main__':

    # set current user
    g_facebook.current_user = load_user(xiaoxiao_id, facebook=g_facebook)

    # create client and connect to the station
    client = Terminal()
    dims_connect(terminal=client, messenger=g_messenger, station=g_station)

    # start scanner
    scanner = FreshmenScanner(messenger=g_messenger)
    scanner.start()
