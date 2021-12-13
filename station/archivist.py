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
    DIM Search Engine
    ~~~~~~~~~~~~~~~~~

    Managing meta & documents
"""

import threading
import traceback
from typing import Optional, Dict, List, Any

from ipx import SharedMemoryArrow
from startrek.fsm import Runner
from startrek import DeparturePriority

from dimp import NetworkType, ID, Meta
from dimp import Envelope, InstantMessage, ReliableMessage
from dimp import Content, Command
from dimp import MetaCommand, DocumentCommand
from dimp import Transceiver
from dimsdk import CommandProcessor, ProcessorFactory
from dimsdk import Station

import sys
import os

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils.log import Log, Logging
from libs.utils.ipc import ArrowDelegate, ArchivistArrows
from libs.common import SearchCommand
from libs.database import FrequencyChecker

from libs.server import ServerProcessor, ServerProcessorFactory
from libs.server import ServerMessenger

from etc.cfg_init import all_stations, neighbor_stations, g_database
from station.config import g_facebook


#
#   User Info Cache
#
g_cached_user_info: Dict[ID, str] = {}          # user ID -> user info

g_info = {
    'users': [],  # all user ID list
    'loading': False,
}

user_id_types = [NetworkType.MAIN, NetworkType.BTC_MAIN, NetworkType.ROBOT]


def reload_user_info():
    """ Scan all users """
    if g_info.get('loading'):
        return False
    g_info['loading'] = True
    users = []
    documents = g_database.scan_documents()
    for doc in documents:
        # check ID
        identifier = doc.identifier
        if identifier is None or identifier.type not in user_id_types:
            # ignore
            continue
        # get name
        name = doc.name
        if name is None:
            info = str(identifier)
        else:
            info = '%s %s' % (identifier, name)
        # cache
        g_cached_user_info[identifier] = info.lower()
        users.append(identifier)
    g_info['users'] = users
    g_info['loading'] = False


def search(keywords: List[str], start: int, limit: int) -> (List[ID], dict):
    users: List[ID] = []
    results = {}
    if limit > 0:
        end = start + limit
    else:
        end = 10240
    index = -1
    all_users = g_info.get('users')
    for identifier in all_users:
        match = True
        # 1. check each keyword with user info
        info = g_cached_user_info.get(identifier, '')
        for kw in keywords:
            if len(kw) > 0 > info.find(kw):
                match = False
                break
        if not match:
            continue
        # 2. check user meta
        meta = g_facebook.meta(identifier=identifier)
        if meta is None:
            # user meta not found, skip
            continue
        # 3. check limit
        index += 1
        if index < start:
            # skip
            continue
        elif index < end:
            # got it
            users.append(identifier)
            if limit > 0:
                # get meta when limit is set
                results[str(identifier)] = meta.dictionary
        elif index >= end:
            # mission accomplished
            break
    return users, results


def recent_users(start: int, limit: int) -> (list, dict):
    all_users = set()
    for station in all_stations:
        users = g_database.get_online_users(station=station.identifier)
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
    if limit > 0:
        # get meta when limit is set
        for item in users:
            meta = g_facebook.meta(identifier=item)
            if meta is not None:
                results[str(item)] = meta.dictionary
    return users, results


def save_response(station: ID, users: List[ID], results: dict):
    for key, value in results.items():
        identifier = ID.parse(identifier=key)
        meta = Meta.parse(meta=value)
        if identifier is not None and meta is not None:
            # assert meta.match_identifier(identifier=identifier), 'meta error'
            g_facebook.save_meta(meta=meta, identifier=identifier)
    # store in redis server
    for item in users:
        g_database.add_online_user(station=station, user=item)
    # clear expired users
    g_database.remove_offline_users(station=station, users=[])
    # NOTICE: online users will be updated by monitor
    #         when login command or online/offline reports received


def send_command(cmd: Command, stations: List[Station]):
    user = g_facebook.current_user
    for station in stations:
        env = Envelope.create(sender=user.identifier, receiver=station.identifier)
        msg = InstantMessage.create(head=env, body=cmd)
        g_messenger.send_instant_message(msg=msg, priority=DeparturePriority.NORMAL)


#
#   DIMP
#


class SearchCommandProcessor(CommandProcessor, Logging):

    def __init__(self, messenger):
        super().__init__(messenger=messenger)

    # Override
    def execute(self, cmd: Command, msg: ReliableMessage) -> List[Content]:
        assert isinstance(cmd, SearchCommand), 'command error: %s' % cmd
        if cmd.users is not None or cmd.results is not None:
            # this is a response
            self.info('saving search respond: %s' % cmd)
            save_response(station=msg.sender, users=cmd.users, results=cmd.results)
            return []
        # this is a request
        keywords = cmd.keywords
        if keywords is None:
            # return [TextContent(text='Search command error')]
            self.error('Search command error: %s' % cmd)
            return []
        keywords = keywords.lower()
        if keywords == SearchCommand.ONLINE_USERS:
            # let the station to do the job
            return []
        elif keywords == 'all users':
            users, results = recent_users(start=cmd.start, limit=cmd.limit)
            self.info('Got %d recent online user(s)' % len(results))
        else:
            users, results = search(keywords=keywords.split(' '), start=cmd.start, limit=cmd.limit)
            self.info('Got %d account(s) matched %s' % (len(results), cmd.keywords))
        # respond
        res = SearchCommand.respond(request=cmd, keywords=keywords, users=users, results=results)
        return [res]


class ArchivistProcessorFactory(ServerProcessorFactory):

    # Override
    def _create_command_processor(self, msg_type: int, cmd_name: str) -> Optional[CommandProcessor]:
        # search
        if cmd_name == SearchCommand.SEARCH:
            return SearchCommandProcessor(messenger=self.messenger)
        elif cmd_name == SearchCommand.ONLINE_USERS:
            # share the same processor
            cpu = self._get_command_processor(cmd_name=SearchCommand.SEARCH)
            if cpu is None:
                cpu = SearchCommandProcessor(messenger=self.messenger)
                self._put_command_processor(cmd_name=SearchCommand.SEARCH, cpu=cpu)
            return cpu
        # others
        return super()._create_command_processor(msg_type=msg_type, cmd_name=cmd_name)


class ArchivistMessageProcessor(ServerProcessor):

    # Override
    def _create_processor_factory(self) -> ProcessorFactory:
        return ArchivistProcessorFactory(messenger=self.messenger)


class ArchivistMessenger(ServerMessenger, ArrowDelegate):

    def __init__(self):
        super().__init__()
        # shared memory pipe
        arrows = ArchivistArrows.secondary(delegate=self)
        self.__income_arrow = arrows[0]
        self.__outgo_arrow = arrows[1]

    # Override
    def _create_processor(self) -> Transceiver.Processor:
        return ArchivistMessageProcessor(messenger=self)

    # Override
    def deliver_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        self.__outgo_arrow.send(obj=msg.dictionary)
        return []

    # Override
    def _deliver(self, msg: ReliableMessage) -> Optional[Content]:
        self.__outgo_arrow.send(obj=msg.dictionary)
        return None

    # Override
    def arrow_received(self, obj: Any, arrow: SharedMemoryArrow):
        assert isinstance(obj, dict), 'event error: %s' % obj
        g_worker.append(msg=obj)

    # Override
    def send_reliable_message(self, msg: ReliableMessage, priority: int) -> bool:
        g_worker.append(msg=msg.dictionary)
        return True

    # Override
    def send_instant_message(self, msg: InstantMessage, priority: int) -> bool:
        s_msg = g_messenger.encrypt_message(msg=msg)
        if s_msg is None:
            # public key not found?
            return False
        r_msg = g_messenger.sign_message(msg=s_msg)
        if r_msg is None:
            # TODO: set msg.state = error
            raise AssertionError('failed to sign message: %s' % s_msg)
        self.send_reliable_message(msg=r_msg, priority=priority)

    # Override
    def send_content(self, content: Content, priority: int, receiver: ID, sender: ID = None) -> bool:
        if sender is None:
            user = g_messenger.facebook.current_user
            assert user is not None, 'current user not set'
            sender = user.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        msg = InstantMessage.create(head=env, body=content)
        return self.send_instant_message(msg=msg, priority=priority)


#
#   Worker
#


class ArchivistWorker(Runner, Logging):

    # each query will be expired after 10 minutes
    QUERY_EXPIRES = 600  # seconds

    def __init__(self):
        super().__init__()
        self.__messages = []
        self.__lock = threading.Lock()
        # for checking duplicated queries
        self.__users_queries: FrequencyChecker[str] = FrequencyChecker()
        self.__meta_queries: FrequencyChecker[ID] = FrequencyChecker(expires=self.QUERY_EXPIRES)
        self.__document_queries: FrequencyChecker[ID] = FrequencyChecker(expires=self.QUERY_EXPIRES)

    def append(self, msg: dict):
        with self.__lock:
            self.__messages.append(msg)

    def shift(self) -> Optional[dict]:
        with self.__lock:
            if len(self.__messages) > 0:
                return self.__messages.pop(0)

    # Override
    def process(self) -> bool:
        msg = None
        try:
            msg = self.shift()
            if msg is None:
                self.__scan_all_users()
                self.__query_online_users()
                self.__query_metas()
                self.__query_documents()
            else:
                msg = ReliableMessage.parse(msg=msg)
                responses = g_messenger.process_reliable_message(msg=msg)
                for res in responses:
                    g_messenger.send_reliable_message(msg=res, priority=DeparturePriority.NORMAL)
                return True
        except Exception as error:
            self.error('archivist error: %s, %s' % (msg, error))
            traceback.print_exc()

    def __scan_all_users(self):
        if self.__users_queries.expired(key='all-documents'):
            self.info('scanning documents...')
            reload_user_info()

    def __query_online_users(self):
        if self.__users_queries.expired(key='online-users', expires=300):
            self.info('querying online users from %d station(s)' % len(all_stations))
            cmd = SearchCommand(keywords=SearchCommand.ONLINE_USERS)
            cmd.limit = -1
            send_command(cmd=cmd, stations=all_stations)

    def __query_metas(self):
        while self.running:
            identifier = g_database.pop_meta_query()
            if identifier is None:
                # no more task
                break
            elif self.__meta_queries.expired(key=identifier):
                self.info('querying meta: %s from %d station(s)' % (identifier, len(neighbor_stations)))
                cmd = MetaCommand.query(identifier=identifier)
                send_command(cmd=cmd, stations=neighbor_stations)

    def __query_documents(self):
        while self.running:
            identifier = g_database.pop_document_query()
            if identifier is None:
                # no more task
                break
            elif self.__document_queries.expired(key=identifier):
                self.info('querying document: %s from %d station(s)' % (identifier, len(neighbor_stations)))
                doc = g_facebook.document(identifier=identifier)
                if doc is None:
                    signature = None
                else:
                    signature = doc.get('signature')  # Base64
                cmd = DocumentCommand.query(identifier=identifier, signature=signature)
                send_command(cmd=cmd, stations=neighbor_stations)


g_messenger = ArchivistMessenger()


if __name__ == '__main__':
    Log.info(msg='>>> starting search engine ...')
    # set current user
    bot_id = ID.parse(identifier='archivist')
    g_facebook.current_user = g_facebook.user(identifier=bot_id)
    g_worker = ArchivistWorker()
    g_worker.run()
    Log.info(msg='>>> search engine exists.')
