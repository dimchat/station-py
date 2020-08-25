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
from typing import Optional, Union

from dimp import ID
from dimp import InstantMessage, ReliableMessage
from dimp import Content, TextContent
from dimsdk import Station
from dimsdk import LoginCommand
from dimsdk import CommandProcessor

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)
sys.path.append(os.path.join(rootPath, 'libs'))

from libs.common import Log, Database

from libs.client import Terminal, ClientMessenger

from robots.config import g_facebook, g_keystore, g_station, g_database, g_released
from robots.config import load_station, dims_connect, all_stations


class LoginCommandProcessor(CommandProcessor):

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    @property
    def database(self) -> Database:
        return self.get_context('database')

    def __roaming(self, cmd: LoginCommand, sender: ID) -> Optional[ID]:
        # check time expires
        old = self.database.login_command(identifier=sender)
        if old is not None:
            if cmd.time < old.time:
                return None
        # get station ID
        assert cmd.station is not None, 'login command error: %s' % cmd
        sid = self.facebook.identifier(cmd.station.get('ID'))
        if sid == g_station.identifier:
            return None
        return sid

    #
    #   main
    #
    def process(self, content: Content, sender: ID, msg: ReliableMessage) -> Optional[Content]:
        assert isinstance(content, LoginCommand), 'command error: %s' % content
        # check roaming
        sid = self.__roaming(cmd=content, sender=sender)
        if sid is not None:
            self.info('%s is roamer to: %s' % (sender, sid))
            octopus.roaming(roamer=sender, station=sid)
        # update login info
        if not self.database.save_login(cmd=content, sender=sender, msg=msg):
            return None
        # respond nothing
        return None


# register
CommandProcessor.register(command='login', processor_class=LoginCommandProcessor)


class InnerMessenger(ClientMessenger):
    """ Messenger for processing message from local station """

    def __init__(self):
        super().__init__()
        self.accepted = False

    # Override
    def process_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        if self.accepted:
            return octopus.departure(msg=msg)
        else:
            return super().process_message(msg=msg)


class OuterMessenger(ClientMessenger):
    """ Messenger for processing message from remote station """

    def __init__(self):
        super().__init__()
        self.accepted = False

    # Override
    def process_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        if self.accepted:
            return octopus.arrival(msg=msg)
        else:
            return super().process_message(msg=msg)


class OctopusClient(Terminal):

    def handshake_success(self):
        super().handshake_success()
        station = self.messenger.get_context('station')
        self.info('start bridge for: %s' % station)
        self.messenger.accepted = True


class Octopus:

    def __init__(self):
        super().__init__()
        self.__neighbors = []  # ID list
        self.__clients = {}    # ID -> Terminal

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    def add_neighbor(self, station: Union[Station, ID]) -> bool:
        if isinstance(station, Station):
            station = station.identifier
        else:
            assert isinstance(station, ID), 'station ID error: %s' % station
        if station == g_station.identifier:
            return False
        if station in self.__neighbors:
            return False
        self.__neighbors.append(station)
        return True

    def __get_client(self, identifier: ID) -> Terminal:
        client = self.__clients.get(identifier)
        if client is None:
            if identifier == g_station.identifier:
                messenger = g_messenger
                station = g_station
            else:
                messenger = OuterMessenger()
                messenger.barrack = g_facebook
                messenger.key_cache = g_keystore
                messenger.context['database'] = g_database
                # client for remote station
                station = load_station(identifier=identifier, facebook=g_facebook)
                assert isinstance(station, Station), 'station error: %s' % identifier
            # create client for station with octopus and messenger
            client = OctopusClient()
            client.octopus = octopus
            dims_connect(terminal=client, messenger=messenger, station=station)
            self.__clients[identifier] = client
        return client

    def __remove_client(self, identifier: ID):
        client = self.__clients.get(identifier)
        if client is not None:
            client.octopus = None
            client.messenger = None
            client.station = None
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
        i_msg = InstantMessage.new(content=content, sender=sender, receiver=receiver)
        s_msg = g_messenger.encrypt_message(msg=i_msg)
        if s_msg is None:
            self.error('failed to encrypt msg: %s' % i_msg)
            return None
        return g_messenger.sign_message(msg=s_msg)

    def departure(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        receiver = g_facebook.identifier(msg.envelope.receiver)
        if receiver == g_station.identifier:
            self.info('msg for %s will be stopped here' % receiver)
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
                self.info('station %s in sent list, ignore this neighbor' % sid)
                continue
            if self.__deliver_message(msg=msg, neighbor=sid):
                success += 1
        # FIXME: what about the failures
        if g_released:
            # FIXME: how to let the client knows where the message reached
            return None
        # response
        sender = g_facebook.identifier(msg.envelope.sender)
        meta = g_facebook.meta(identifier=sender)
        if meta is None:
            # waiting for meta
            return None
        text = 'Message broadcast to %d/%d stations' % (success, len(neighbors))
        self.info('outgo: %s, %s | %s | %s' % (text, msg['signature'][:8], sender.name, msg.envelope.receiver))
        res = TextContent.new(text=text)
        res.group = msg.envelope.group
        return self.__pack_message(content=res, receiver=sender)

    def __traced(self, msg: ReliableMessage, station: Station) -> bool:
        sid = station.identifier
        traces = msg.get('traces')
        if traces is not None:
            for node in traces:
                if isinstance(node, str):
                    return sid == node
                elif isinstance(node, dict):
                    return sid == node.get('ID')
                else:
                    self.error('traces node error: %s' % node)

    def arrival(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        sid = g_station.identifier
        if self.__traced(msg=msg, station=g_station):
            self.info('current station %s in traces list, ignore this message: %s' % (sid, msg))
            return None
        if not self.__deliver_message(msg=msg, neighbor=sid):
            self.error('failed to send income message: %s' % msg)
            return None
        if g_released:
            # FIXME: how to let the client knows where the message reached
            return None
        # response
        sender = g_facebook.identifier(msg.envelope.sender)
        text = 'Message reached station: %s' % g_station
        self.info('income: %s, %s | %s | %s' % (text, msg['signature'][:8], sender.name, msg.envelope.receiver))
        res = TextContent.new(text=text)
        res.group = msg.envelope.group
        return self.__pack_message(content=res, receiver=sender)

    def roaming(self, roamer: ID, station: ID) -> int:
        sent_count = 0
        while True:
            # 1. scan offline messages
            self.info('%s is roaming, scanning messages for it' % roamer)
            batch = g_database.load_message_batch(roamer)
            if batch is None:
                self.info('no message for this roamer: %s' % roamer)
                return sent_count
            messages = batch.get('messages')
            if messages is None or len(messages) == 0:
                self.error('message batch error: %s' % batch)
                # raise AssertionError('message batch error: %s' % batch)
                continue
            self.info('got %d message(s) for %s' % (len(messages), roamer))
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
            self.info('a batch message(%d/%d) redirect for %s' % (count, total_count, roamer))
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
g_messenger.barrack = g_facebook
g_messenger.key_cache = g_keystore
g_messenger.context['database'] = g_database
g_facebook.messenger = g_messenger


if __name__ == '__main__':

    # set current user
    g_facebook.current_user = g_station

    octopus = Octopus()
    # add neighbors
    for s in all_stations:
        octopus.add_neighbor(station=s)
    octopus.connect()
