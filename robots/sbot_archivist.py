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

"""
    Search Engine
    ~~~~~~~~~~~~~

    Station Bot for searching users
"""

import sys
import os
import threading
import time
from typing import Optional, List

from dimp import NetworkType, ID, Meta
from dimp import Envelope, InstantMessage, ReliableMessage
from dimp import Content, TextContent, Command
from dimsdk import CommandProcessor

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Logging
from libs.common import SearchCommand
from libs.common import Storage, Database
from libs.client import Terminal, ClientMessenger, Server

from robots.config import g_station, all_stations
from robots.config import dims_connect

from etc.cfg_loader import load_user

#
#   User Info Cache
#
g_cached_user_info = {}     # user ID -> user info
g_cached_online_users = {}  # station ID -> user list


def reload():
    users = []
    documents = g_database.scan_documents()
    for doc in documents:
        identifier = doc.identifier
        info = str(identifier).lower()
        name = doc.name
        if name is not None:
            info += ' ' + name.lower()
        g_cached_user_info[identifier] = info
        users.append(identifier)
    g_cached_user_info['users'] = users


def search(keywords: List[str], start: int, limit: int) -> (list, dict):
    results = {}
    if limit <= 0:
        end = 1024
    else:
        end = start + limit
    index = -1
    users = g_cached_user_info.get('users', [])
    for identifier in users:
        if not isinstance(identifier, ID):
            # 'expired'
            continue
        if identifier.type not in [NetworkType.MAIN, NetworkType.BTC_MAIN, NetworkType.ROBOT]:
            # ignore
            continue
        match = True
        info = g_cached_user_info.get(identifier, '')
        for kw in keywords:
            if len(kw) > 0 > info.find(kw):
                match = False
                break
        if match:
            meta = g_facebook.meta(identifier=identifier)
            if meta is not None:
                index += 1
                if index >= end:
                    # mission accomplished
                    break
                elif index >= start:
                    # got it
                    results[str(identifier)] = meta.dictionary
    return list(results.keys()), results


def recent_users(start: int, limit: int) -> (list, dict):
    all_users = set()
    for station in all_stations:
        users = load_users(station.identifier)
        for item in users:
            all_users.add(item)
    # user ID list
    users = list(all_users)
    end = len(users)
    if limit > 0:
        if start + limit < len(users):
            end = start + limit
        else:
            end = len(users)
    users = users[start:end]
    # user meta list
    results = {}
    for item in users:
        meta = g_facebook.meta(identifier=item)
        if meta is not None:
            results[str(item)] = meta.dictionary
    return users, results


def load_users(station: ID) -> List[ID]:
    # path = os.path.join(Storage.root, 'protected', str(station.address), 'online_users.txt')
    # text = Storage.read_text(path=path)
    # if text is None:
    #     return []
    # else:
    #     return ID.convert(members=text.splitlines())
    return g_cached_online_users.get(station)


def save_users(station: ID, users: List[ID]) -> bool:
    g_cached_online_users[station] = users
    """ Save online users in a text file
        file path: '.dim/protected/{ADDRESS}/online_users.txt' """
    array = ID.revert(members=users)
    text = '\n'.join(array)
    path = os.path.join(Storage.root, 'protected', str(station.address), 'online_users.txt')
    return Storage.write_text(text=text, path=path)


def save_response(station: ID, users: List[ID], results: dict) -> Optional[Content]:
    for key, value in results.items():
        identifier = ID.parse(identifier=key)
        meta = Meta.parse(meta=value)
        if identifier is not None and meta is not None:
            # assert meta.match_identifier(identifier=identifier), 'meta error'
            g_facebook.save_meta(meta=meta, identifier=identifier)
    if save_users(station=station, users=users):
        # respond nothing
        return None


class SearchCommandProcessor(CommandProcessor, Logging):

    def __init__(self):
        super().__init__()
        self.__query_expired = 0
        self.__scan_expired = 0

    @property
    def messenger(self) -> ClientMessenger:
        return super().messenger

    @messenger.setter
    def messenger(self, transceiver: ClientMessenger):
        CommandProcessor.messenger.__set__(self, transceiver)

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, SearchCommand), 'command error: %s' % cmd
        if cmd.users is not None or cmd.results is not None:
            # this is a response
            self.info('saving search respond: %s' % cmd)
            return save_response(station=msg.sender, users=cmd.users, results=cmd.results)
        # this is a request
        keywords = cmd.keywords
        if keywords is None:
            return TextContent(text='Search command error')
        keywords = keywords.lower()
        if keywords == SearchCommand.ONLINE_USERS:
            # let the station to do the job
            return None
        elif keywords == 'all users':
            # query all online users (last 5 minutes)
            self.query_online_users()
            users, results = recent_users(start=cmd.start, limit=cmd.limit)
            self.info('Got %d recent online user(s)' % len(results))
        else:
            self.scan_all_users()
            users, results = search(keywords=keywords.split(' '), start=cmd.start, limit=cmd.limit)
            self.info('Got %d account(s) matched %s' % (len(results), cmd.keywords))
        # respond
        info = cmd.copy_dictionary(False)
        info.pop('sn', None)
        info.pop('time', None)
        cmd = SearchCommand(cmd=info)
        cmd.station = g_station.identifier
        cmd.users = users
        cmd.results = results
        return cmd

    def query_online_users(self) -> bool:
        now = int(time.time())
        if now < self.__query_expired:
            return False
        user = g_facebook.current_user
        if self.__query_expired == 0:
            # first time, query stations with meta & visa as attachments
            meta = user.meta
            meta = meta.dictionary
            visa = user.visa
            if visa is not None:
                visa = visa.dictionary
        else:
            meta = None
            visa = None
        self.__query_expired = now + 120  # update next 2 minutes at least
        # search command
        cmd = SearchCommand(keywords=SearchCommand.ONLINE_USERS)
        cmd.limit = -1
        messenger = self.messenger
        cnt = 0
        for station in all_stations:
            self.info('querying online users: %s' % station)
            env = Envelope.create(sender=user.identifier, receiver=station.identifier)
            msg = InstantMessage.create(head=env, body=cmd)
            if meta is not None:
                msg['meta'] = meta
                msg['visa'] = visa
            if messenger.send_message(msg=msg):
                cnt += 1
        return cnt > 0

    def scan_all_users(self) -> bool:
        now = int(time.time())
        if now > self.__scan_expired:
            self.__scan_expired = now + 1800  # expired 30 minutes at least
            self.info('scanning documents...')
            threading.Thread(target=reload).start()
            return True


# register
spu = SearchCommandProcessor()
CommandProcessor.register(command=SearchCommand.SEARCH, cpu=spu)
CommandProcessor.register(command=SearchCommand.ONLINE_USERS, cpu=spu)


class ArchivistMessenger(ClientMessenger):

    def handshake_accepted(self, server: Server):
        super().handshake_accepted(server=server)
        # refresh data
        time.sleep(2)
        spu.messenger = g_messenger
        spu.query_online_users()
        spu.scan_all_users()


g_database = Database()
g_messenger = ArchivistMessenger()
g_facebook = g_messenger.facebook


if __name__ == '__main__':

    # set current user
    archivist = ID.parse(identifier='archivist')
    g_facebook.current_user = load_user(identifier=archivist, facebook=g_facebook)

    # create client and connect to the station
    client = Terminal()
    dims_connect(terminal=client, messenger=g_messenger, server=g_station)
