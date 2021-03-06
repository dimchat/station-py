#! /usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# MIT License
#
# Copyright (c) 2020 Albert Moky
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
    Station bot: 'Octopus'
    ~~~~~~~~~~~~~~~~~~~~~~

    Bot for bridging neighbor stations
"""

import sys
import os
from typing import Optional, Union, Set, Dict

from dimp import ID
from dimp import Envelope, InstantMessage, ReliableMessage
from dimp import Content, TextContent, Command
from dimsdk import Station
from dimsdk import LoginCommand
from dimsdk import CommandProcessor

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Logging
from libs.common import Database
from libs.common import msg_traced, roaming_station

from libs.client import Server, Terminal, ClientFacebook, ClientMessenger

from robots.config import g_station, g_released
from robots.config import load_station, dims_connect, all_stations


g_facebook = ClientFacebook()
g_database = Database()


class LoginCommandProcessor(CommandProcessor, Logging):

    def execute(self, cmd: Command, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(cmd, LoginCommand), 'command error: %s' % cmd
        sender = msg.sender
        # check roaming
        sid = roaming_station(g_database, sender, cmd=cmd, msg=msg)
        if sid is not None and sid != g_station.identifier:
            self.info('%s is roamer to: %s' % (sender, sid))
            octopus.roaming(roamer=sender, station=sid)
        # respond nothing
        return None


# register
CommandProcessor.register(command=Command.LOGIN, cpu=LoginCommandProcessor())


class InnerMessenger(ClientMessenger):
    """ Messenger for processing message from local station """

    def __init__(self):
        super().__init__()
        self.__accepted = False

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        self.info('outgoing message: %s -> %s' % (msg.sender, msg.receiver))
        if self.__accepted:
            if msg.delegate is None:
                msg.delegate = self
            return octopus.departure(msg=msg)
        else:
            return super().process_reliable_message(msg=msg)

    def handshake_accepted(self, server: Server):
        super().handshake_accepted(server=server)
        self.info('start bridge for: %s' % self.server)
        self.__accepted = True


class OuterMessenger(ClientMessenger):
    """ Messenger for processing message from remote station """

    def __init__(self):
        super().__init__()
        self.__accepted = False

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        self.info('incoming message: %s -> %s' % (msg.sender, msg.receiver))
        if self.__accepted:
            if msg.delegate is None:
                msg.delegate = self
            return octopus.arrival(msg=msg)
        else:
            return super().process_reliable_message(msg=msg)

    def handshake_accepted(self, server: Server):
        super().handshake_accepted(server=server)
        self.info('start bridge for: %s' % self.server)
        self.__accepted = True


class Octopus(Logging):

    def __init__(self):
        super().__init__()
        self.__neighbors: Set[ID] = set()        # station ID list
        self.__clients: Dict[ID, Terminal] = {}  # ID -> Terminal

    def add_neighbor(self, station: Union[Station, ID]) -> bool:
        if isinstance(station, Station):
            station = station.identifier
        else:
            assert isinstance(station, ID), 'station ID error: %s' % station
        if station == g_station.identifier:
            return False
        if station in self.__neighbors:
            return False
        self.__neighbors.add(station)
        return True

    def __get_client(self, identifier: ID) -> Terminal:
        client = self.__clients.get(identifier)
        if client is None:
            if identifier == g_station.identifier:
                messenger = g_messenger
                server = g_station
            else:
                messenger = OuterMessenger()
                # client for remote station
                server = load_station(identifier=identifier, facebook=g_facebook)
                assert isinstance(server, Station), 'station error: %s' % identifier
            if not isinstance(server, Server):
                server = Server(identifier=identifier, host=server.host, port=server.port)
                g_facebook.cache_user(user=server)
            # create client for station with octopus and messenger
            client = Terminal()
            dims_connect(terminal=client, messenger=messenger, server=server)
            self.__clients[identifier] = client
        return client

    def __remove_client(self, identifier: ID):
        client = self.__clients.get(identifier)
        if isinstance(client, Terminal):
            client.messenger = None
            client.stop()
            self.__clients.pop(identifier)

    def __deliver_message(self, msg: ReliableMessage, neighbor: ID) -> bool:
        client = self.__get_client(identifier=neighbor)
        if client is None:
            self.error('neighbor station %s not connected' % neighbor)
            return False
        if client.messenger.send_message(msg=msg):
            # send message OK
            return True
        else:
            self.error('failed to deliver message, remove the bridge: %s' % neighbor)
            self.__remove_client(identifier=neighbor)
            return False

    def __pack_message(self, content: Content, receiver: ID) -> Optional[ReliableMessage]:
        sender = g_station.identifier
        env = Envelope.create(sender=sender, receiver=receiver)
        i_msg = InstantMessage.create(head=env, body=content)
        s_msg = g_messenger.encrypt_message(msg=i_msg)
        if s_msg is None:
            self.error('failed to encrypt msg: %s' % i_msg)
            return None
        return g_messenger.sign_message(msg=s_msg)

    def departure(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        receiver = msg.receiver
        if receiver == g_station.identifier:
            self.debug('msg for %s will be stopped here' % receiver)
            return None
        sent_neighbors = msg.get('sent_neighbors')
        if sent_neighbors is None:
            sent_neighbors = []
        else:
            msg.pop('sent_neighbors')
        neighbors = self.__neighbors.copy()
        success = 0
        for sid in neighbors:
            if sid in sent_neighbors:
                self.debug('station %s in sent list, ignore this neighbor' % sid)
                continue
            if self.__deliver_message(msg=msg, neighbor=sid):
                success += 1
        # FIXME: what about the failures
        if g_released:
            # FIXME: how to let the client knows where the message reached
            return None
        # response
        sender = msg.sender
        meta = g_facebook.meta(identifier=sender)
        if meta is None:
            # waiting for meta
            return None
        text = 'Message broadcast to %d/%d stations' % (success, len(neighbors))
        self.debug('outgo: %s, %s | %s | %s' % (text, msg['signature'][:8], sender.name, msg.receiver))
        res = TextContent(text=text)
        res.group = msg.group
        return self.__pack_message(content=res, receiver=sender)

    def arrival(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        # check message delegate
        sid = g_station.identifier
        if msg_traced(msg=msg, node=sid):
            self.debug('current station %s in traces list, ignore this message: %s' % (sid, msg))
            return None
        if not self.__deliver_message(msg=msg, neighbor=sid):
            self.error('failed to send income message: %s' % msg)
            return None
        if g_released:
            # FIXME: how to let the client knows where the message reached
            return None
        # response
        sender = msg.sender
        text = 'Message reached station: %s' % g_station
        self.debug('income: %s, %s | %s | %s' % (text, msg['signature'][:8], sender.name, msg.receiver))
        res = TextContent(text=text)
        res.group = msg.group
        return self.__pack_message(content=res, receiver=sender)

    def roaming(self, roamer: ID, station: ID) -> int:
        sent_count = 0
        while True:
            # 1. scan offline messages
            self.debug('%s is roaming, scanning messages for it' % roamer)
            batch = g_database.load_message_batch(roamer)
            if batch is None:
                self.debug('no message for this roamer: %s' % roamer)
                return sent_count
            messages = batch.get('messages')
            if messages is None or len(messages) == 0:
                self.error('message batch error: %s' % batch)
                # raise AssertionError('message batch error: %s' % batch)
                continue
            self.debug('got %d message(s) for %s' % (len(messages), roamer))
            # 2. redirect offline messages one by one
            count = 0
            for msg in messages:
                success = self.__deliver_message(msg=msg, neighbor=station)
                if success > 0:
                    # redirect message success (at least one)
                    count = count + 1
                else:
                    # redirect message failed, remove session here?
                    break
            # 3. remove messages after success
            total_count = len(messages)
            self.debug('a batch message(%d/%d) redirect for %s' % (count, total_count, roamer))
            g_database.remove_message_batch(batch, removed_count=count)
            sent_count += count
            if count < total_count:
                self.error('redirect message failed(%d/%d) for: %s' % (count, total_count, roamer))
                return sent_count

    def connect(self):
        #
        #   Local Station
        #
        self.__get_client(identifier=g_station.identifier)
        #
        #   Remote Stations
        #
        neighbors = self.__neighbors.copy()
        for sid in neighbors:
            self.__get_client(identifier=sid)


"""
    Messenger for Local Station Bridge
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = InnerMessenger()


if __name__ == '__main__':

    # set current user
    g_facebook.current_user = g_station

    octopus = Octopus()
    # add neighbors
    for s in all_stations:
        octopus.add_neighbor(station=s)
    octopus.connect()
