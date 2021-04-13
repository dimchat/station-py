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
import threading
import time
import traceback
from typing import Optional, Union, Dict, List

from dimp import ID
from dimp import Envelope, InstantMessage, ReliableMessage
from dimp import Content, TextContent
from dimsdk import Station

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Logging
from libs.common import Database
from libs.common import msg_traced

from libs.client import Server, Terminal, ClientFacebook, ClientMessenger

from robots.config import g_station, g_released
from robots.config import load_station, dims_connect, all_stations


g_facebook = ClientFacebook()
g_database = Database()


class OctopusMessenger(ClientMessenger):

    def __init__(self):
        super().__init__()
        self.__accepted = False

    @property
    def accepted(self) -> bool:
        return self.__accepted

    @accepted.setter
    def accepted(self, value: bool):
        self.__accepted = value

    def reconnected(self):
        self.accepted = False


class InnerMessenger(OctopusMessenger):
    """ Messenger for processing message from local station """

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        self.info('outgoing message: %s -> %s' % (msg.sender, msg.receiver))
        if self.accepted or msg.receiver != g_station.identifier:
            if msg.delegate is None:
                msg.delegate = self
            return octopus.departure(msg=msg)
        else:
            return super().process_reliable_message(msg=msg)

    def handshake_accepted(self, server: Server):
        super().handshake_accepted(server=server)
        self.info('start bridge for: %s' % self.server)
        self.accepted = True


class OuterMessenger(OctopusMessenger):
    """ Messenger for processing message from remote station """

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        self.info('incoming message: %s -> %s' % (msg.sender, msg.receiver))
        if self.accepted or msg.receiver != g_station.identifier:
            if msg.delegate is None:
                msg.delegate = self
            return octopus.arrival(msg=msg)
        else:
            return super().process_reliable_message(msg=msg)

    def handshake_accepted(self, server: Server):
        super().handshake_accepted(server=server)
        self.info('start bridge for: %s' % self.server)
        self.accepted = True


class Worker(threading.Thread, Logging):
    """ Client-Server connection keeper """

    def __init__(self, client: Terminal, server: Server, messenger: ClientMessenger):
        super().__init__()
        self.__running = True
        self.__client = dims_connect(terminal=client, messenger=messenger, server=server)
        self.__waiting_list: List[ReliableMessage] = []  # sending messages
        self.__lock = threading.Lock()

    @property
    def client(self) -> Terminal:
        return self.__client

    def add_msg(self, msg: ReliableMessage):
        with self.__lock:
            self.__waiting_list.append(msg)

    def pop_msg(self) -> Optional[ReliableMessage]:
        with self.__lock:
            if len(self.__waiting_list) > 0:
                return self.__waiting_list.pop(0)

    def __send(self, msg: ReliableMessage) -> bool:
        client = self.client
        messenger = client.messenger
        assert isinstance(messenger, OctopusMessenger), 'octopus messenger error: %s' % messenger
        # try to send via exist connection
        if messenger.send_message(msg=msg):
            return True
        # reconnecting
        self.info('waiting for reconnect...')
        time.sleep(32)
        # try again
        return messenger.send_message(msg=msg)

    def run(self):
        while self.__running:
            try:
                while self.__running:
                    msg = self.pop_msg()
                    if msg is None:
                        # waiting queue empty
                        break
                    if not self.__send(msg=msg):
                        self.error('failed to send message, store it: %s' % msg)
                        g_database.store_message(msg=msg)
                        time.sleep(5)
                        break
            except Exception as error:
                self.error('octopus error: %s -> %s' % (self.client.server, error))
                traceback.print_exc()
            finally:
                # sleep for next loop
                time.sleep(0.1)
        self.info('octopus exit: %s' % self.client.server)
        while True:
            msg = self.pop_msg()
            if msg is None:
                break
            else:
                g_database.store_message(msg=msg)

    def stop(self):
        self.__running = False


class Octopus(Logging):

    def __init__(self):
        super().__init__()
        self.__home: Worker = None
        self.__neighbors: Dict[ID, Worker] = {}  # ID -> Worker

    def start(self):
        # local station
        self.__home.start()
        # remote station
        neighbors = self.__neighbors.keys()
        for sid in neighbors:
            self.__neighbors[sid].start()

    def stop(self):
        # remote station
        neighbors = self.__neighbors.keys()
        for sid in neighbors:
            self.__neighbors[sid].stop()
        # local station
        self.__home.stop()

    def add_neighbor(self, station: Union[Station, ID]) -> bool:
        if isinstance(station, Station):
            station = station.identifier
        assert isinstance(station, ID), 'station ID error: %s' % station
        if station == g_station.identifier:
            if self.__home is None:
                # worker for local station
                self.__home = Worker(client=Terminal(), server=g_station, messenger=g_messenger)
                return True
        elif self.__neighbors.get(station) is None:
            # create remote station
            server = load_station(identifier=station, facebook=g_facebook)
            assert isinstance(server, Station), 'station error: %s' % station
            if not isinstance(server, Server):
                server = Server(identifier=station, host=server.host, port=server.port)
                g_facebook.cache_user(user=server)
            # worker for remote station
            self.__neighbors[station] = Worker(client=Terminal(), server=server, messenger=OuterMessenger())
            return True

    def __deliver_message(self, msg: ReliableMessage, neighbor: ID) -> bool:
        if neighbor == g_station.identifier:
            worker = self.__home
        else:
            worker = self.__neighbors.get(neighbor)
        if worker is None:
            self.error('neighbor station %s not defined' % neighbor)
            return False
        else:
            worker.add_msg(msg=msg)
            return True

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
            self.warning('msg for %s will be stopped here' % receiver)
            return None
        success = 0
        target = ID.parse(identifier=msg.get('target'))
        if target is None:
            # broadcast to all neighbors
            all_neighbors = self.__neighbors.copy()
            sent_neighbors = msg.get('sent_neighbors')
            if sent_neighbors is None:
                sent_neighbors = []
            else:
                msg.pop('sent_neighbors')
            for sid in all_neighbors:
                if str(sid) in sent_neighbors:
                    self.debug('station %s in sent list, ignore this neighbor' % sid)
                    continue
                if self.__deliver_message(msg=msg, neighbor=sid):
                    success += 1
                else:
                    self.error('broadcast message failed: %s' % sid)
        else:
            # redirect to single neighbor
            msg.pop('target')
            if self.__deliver_message(msg=msg, neighbor=target):
                success = 1
            else:
                # save roaming message
                g_database.store_message(msg=msg)
        if g_released:
            # FIXME: how to let the client knows where the message reached
            return None
        # response
        sender = msg.sender
        meta = g_facebook.meta(identifier=sender)
        if meta is None:
            # waiting for meta
            return None
        if success is 0:
            text = 'Message cached'
        else:
            text = 'Message forwarded'
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
            g_database.store_message(msg=msg)
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


"""
    Messenger for Local Station Bridge
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
g_messenger = InnerMessenger()


if __name__ == '__main__':

    # set current user
    g_facebook.current_user = g_station

    octopus = Octopus()
    # set local station
    octopus.add_neighbor(g_station)
    # add neighbors
    for s in all_stations:
        octopus.add_neighbor(station=s)
    # start all
    octopus.start()
