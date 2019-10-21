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
    Group bot: 'assistant'
    ~~~~~~~~~~~~~~~~~~~~~~

    Bot for collecting and responding group member list
"""

import sys
import os
import threading
import time

from dimp import ID
from dimp import Content, MetaCommand, ProfileCommand, GroupCommand

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.common import Storage, Log
from libs.client import Robot

from robots.config import g_facebook, g_station
from robots.config import chat_bot
from robots.config import create_daemon, assistant_id, group_naruto


freshmen_file = '/data/.dim/freshmen.txt'
# freshmen_file = '/tmp/freshmen.txt'  # test


class FreshmenScanner(threading.Thread):

    def __init__(self):
        super().__init__()
        gid = g_facebook.identifier(group_naruto)
        self.__group = g_facebook.group(gid)
        self.delegate: Robot = None

    @staticmethod
    def __load_freshmen() -> list:
        freshmen = []
        text = Storage.read_text(freshmen_file)
        if text is not None:
            array = text.splitlines()
            for item in array:
                identifier = g_facebook.identifier(item)
                if identifier is not None:
                    freshmen.append(identifier)
        return freshmen

    def __freshmen(self) -> list:
        users = self.__load_freshmen()
        members = self.__group.members
        if members is not None:
            # remove existed members
            for item in members:
                if item in users:
                    users.remove(item)
        return users

    def __send_content(self, content: Content, receiver: ID) -> bool:
        if self.delegate is not None:
            return self.delegate.send_content(content=content, receiver=receiver)

    def run(self):
        while True:
            time.sleep(30)
            #
            #  1. get freshmen
            #
            freshmen = self.__freshmen()
            if len(freshmen) == 0:
                continue
            #
            #  2. send 'invite' command to existed members
            #
            gid = self.__group.identifier
            members = self.__group.members
            if members is None:
                members = []
            cmd = GroupCommand.invite(group=gid, members=freshmen)
            for item in members:
                self.__send_content(content=cmd, receiver=item)
            Log.info('invite command sent: %s,\n members: %s' % (cmd, members))
            #
            #  3. send group meta to all freshmen
            #
            meta = self.__group.meta
            profile = self.__group.profile
            if profile is None:
                cmd = MetaCommand.response(identifier=gid, meta=meta)
            else:
                cmd = ProfileCommand.response(identifier=gid, profile=profile, meta=meta)
            for item in freshmen:
                self.__send_content(content=cmd, receiver=item)
            Log.info('meta/profile command sent: %s,\n freshmen: %s' % (cmd, freshmen))
            #
            #  4. send 'invite' command to freshmen
            #
            for item in freshmen:
                if item not in members:
                    members.append(item)
            cmd = GroupCommand.invite(group=gid, members=members)
            for item in freshmen:
                self.__send_content(content=cmd, receiver=item)
            Log.info('invite command sent: %s,\n freshmen: %s' % (cmd, freshmen))


if __name__ == '__main__':

    daemon = create_daemon(identifier=assistant_id)
    daemon.bots = [chat_bot('tuling'), chat_bot('xiaoi')]
    daemon.connect(station=g_station)

    scanner = FreshmenScanner()
    scanner.delegate = daemon
    scanner.start()
