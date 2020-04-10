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
    Chat bot: 'TokenTalk Team'
    ~~~~~~~~~~~~~~~~~~~~
"""

import sys
import os
import threading
import time

from dimp import Group
from dimp import TextContent, ProfileCommand, HandshakeCommand, InstantMessage

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.common import Storage
from libs.common import Log

from libs.client import ClientMessenger
from libs.client import GroupManager

from robots.config import g_facebook, g_keystore, g_station
from robots.config import load_freshmen
from robots.config import load_user, create_client
from robots.config import chat_bot, tokentalkteam_id


"""
    Messenger for Chat Bot client
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = ClientMessenger()
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore

# chat bot
g_messenger.context['bots'] = [chat_bot('xiaoi')]
# current station
g_messenger.set_context('station', g_station)

g_facebook.messenger = g_messenger


class FreshmenScanner(threading.Thread):

    def __init__(self, messenger: ClientMessenger):
        super().__init__()
        # delegate for send message
        self.messenger = messenger

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def load_oldmen(self) -> list:
        oldmen = []
        text = Storage.read_text('/data/.dim/oldmen.txt')
        array = None
        if text is not None:
            array = text.splitlines()
        if array is not None:
            for item in array:
                identifier = g_facebook.identifier(item)
                if identifier is None:
                    Log.error('ID error: %s' % item)
                elif identifier.is_user:
                    oldmen.append(identifier)
                else:
                    # Log.error('Not a user ID: %s' % identifier)
                    pass
        return oldmen

    def save_oldmen(self, identifier) -> bool:
        path = '/data/.dim/oldmen.txt'
        line = identifier + '\n'
        Storage.info('saving oldmen: %s' % identifier)
        return Storage.append_text(text=line, path=path)
        
    def __freshmen(self) -> list:
        freshmen = load_freshmen()
        if freshmen is None:
            return []
        # remove existed members
        oldmen = self.load_oldmen()
        for item in oldmen:
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

    def __welcome(self, freshmen: list):
        msgText = 'Hello!'
        # the first message is to let client retrieve meta.
        for item in freshmen:
            content = TextContent.new(text=msgText)
            self.messenger.send_content(content=content, receiver=item)
            self.save_oldmen(item)

        time.sleep(3)
        msgText = 'Welcome!'
        # tokentalkteam_profile = g_facebook.profile(identifier=tokentalkteam_id)
        for item in freshmen:
            # send ProfileCommand
            # cmd = ProfileCommand.new(identifier=tokentalkteam_id, profile=tokentalkteam_profile)
            # msg = InstantMessage.new(content=cmd, sender=tokentalkteam_id, receiver=item)
            # msg = self.messenger.sign_message(self.messenger.encrypt_message(msg=msg))
            # carry meta for first contact
            # msg.meta = g_facebook.meta(item)
            # self.messenger.send_message(msg=msg)
            # time.sleep(3)
            content = TextContent.new(text=msgText)
            self.messenger.send_content(content=content, receiver=item)
            self.save_oldmen(item)

    def __run_unsafe(self):
        #
        #  1. get freshmen 
        #
        freshmen = self.__freshmen()
        if len(freshmen) == 0:
            time.sleep(30)
            return
        self.info('freshmen: %s' % freshmen)
        #
        #  2. send Welcome!
        #
        self.__welcome(freshmen=freshmen)

    def run(self):
        while True:
            time.sleep(30)
            self.info('try to scan freshmen ...')
            try:
                self.__run_unsafe()
            except Exception as error:
                self.error('scan freshmen error: %s' % error)


if __name__ == '__main__':

    user = load_user(tokentalkteam_id)
    client = create_client(user=user, messenger=g_messenger)
    # start scanner
    scanner = FreshmenScanner(messenger=g_messenger)
    scanner.start()
