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
from typing import Optional, Dict, List

from dimp import ID, ReliableMessage
from dimsdk import Station, HandshakeCommand

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils import Logging
from libs.common import msg_traced, is_broadcast_message
from libs.client import Server, Terminal, ClientMessenger

from etc.cfg_init import neighbor_stations, g_database, g_facebook
from robots.config import g_station
from robots.config import dims_connect


class OctopusMessenger(ClientMessenger):

    def __init__(self):
        super().__init__()
        self.__accepted = False

    @property
    def accepted(self) -> bool:
        return self.__accepted

    def connected(self):
        # super().connected()
        self.__accepted = False

    def _is_handshaking(self, msg: ReliableMessage) -> bool:
        i_msg = self.decrypt_message(msg=msg)
        if i_msg is not None:
            return isinstance(i_msg.content, HandshakeCommand)

    # Override
    def handshake_accepted(self, server: Server):
        self.__accepted = True
        self.info('start bridge for: %s' % self.server)
        # super().handshake_accepted(server=server)


class InnerMessenger(OctopusMessenger):
    """ Messenger for processing message from local station """

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        if msg.receiver == g_station.identifier:
            if self._is_handshaking(msg=msg):
                self.info('inner handshaking: %s' % msg.sender)
                return super().process_reliable_message(msg=msg)
            else:
                traces = msg.get('traces')
                self.error('drop inner msg(type=%d): %s -> %s | %s' % (msg.type, msg.sender, msg.receiver, traces))
                return None
        # handshake accepted, delivering message
        self.info('outgoing msg(type=%d): %s -> %s | %s' % (msg.type, msg.sender, msg.receiver, msg.get('traces')))
        if msg.delegate is None:
            msg.delegate = self
        return octopus.departure(msg=msg)


class OuterMessenger(OctopusMessenger):
    """ Messenger for processing message from remote station """

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        if msg.sender == msg.receiver:
            traces = msg.get('traces')
            self.error('drop outer msg(type=%d): %s -> %s | %s' % (msg.type, msg.sender, msg.receiver, traces))
            return None
        if msg.receiver == g_station.identifier:
            if self._is_handshaking(msg=msg):
                self.info('outer handshaking: %s' % msg.sender)
                return super().process_reliable_message(msg=msg)
        # handshake accepted, receiving message
        self.info('incoming msg(type=%d): %s -> %s | %s' % (msg.type, msg.sender, msg.receiver, msg.get('traces')))
        if msg.delegate is None:
            msg.delegate = self
        return octopus.arrival(msg=msg)


class Worker(threading.Thread, Logging):
    """ Client-Server connection keeper """

    def __init__(self, client: Terminal, server: Server, messenger: OctopusMessenger):
        super().__init__()
        self.__running = False
        self.__waiting_list: List[ReliableMessage] = []  # sending messages
        self.__lock = threading.Lock()
        self.__client = dims_connect(terminal=client, messenger=messenger, server=server)
        self.__server = server
        self.__messenger = messenger

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

    def run(self):
        self.setup()
        try:
            self.handle()
        finally:
            self.finish()

    def stop(self):
        self.__running = False

    def setup(self):
        self.__running = True
        while self.__running:
            try:
                # check handshake
                if self.__messenger.accepted:
                    break
                else:
                    self.error('not handshake yet, trying to reconnect')
                    self._reconnect()
            except Exception as error:
                self.error('octopus error: %s -> %s' % (self.__server, error))
                traceback.print_exc()

    def finish(self):
        self.info('octopus exit: %s' % self.client.server)
        while True:
            msg = self.pop_msg()
            if msg is None:
                break
            else:
                g_database.save_message(msg=msg)

    def handle(self):
        while self.__running:
            try:
                # handling
                while self.__running:
                    if self.__messenger.accepted:
                        if not self.process():
                            # waiting queue empty, have a rest
                            self._idle()
                    elif not self._reconnect():
                        # reconnect failed, have a rest
                        self._idle()
            except Exception as error:
                self.error('octopus error: %s -> %s' % (self.client.server, error))
                traceback.print_exc()
            finally:
                self.info('octopus waiting server accepted: %s ...' % self.client.server)
                time.sleep(5)

    def process(self) -> bool:
        msg = self.pop_msg()
        if msg is not None:
            if is_broadcast_message(msg=msg):
                priority = 1  # SLOWER
            else:
                priority = 0  # NORMAL
            if not self.__messenger.send_message(msg=msg, priority=priority):
                self.error('failed to send message, store it: %s -> %s' % (msg.sender, msg.receiver))
                g_database.save_message(msg=msg)
            return True

    def _reconnect(self) -> bool:
        time.sleep(5)
        session = self.__server.connect()
        if session.gate.running:
            self.__server.handshake()
            return True

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.1)


class Octopus(Logging):

    def __init__(self):
        super().__init__()
        self.__home: Optional[Worker] = None
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

    def set_home(self, station: ID) -> bool:
        assert station == g_station.identifier, 'home station ID error: %s, %s' % (station, g_station)
        if self.__home is None:
            # worker for local station
            self.info('bridge for local station: %s' % g_station)
            self.__home = Worker(client=Terminal(), server=g_station, messenger=InnerMessenger())
            return True

    def add_neighbor(self, station: ID) -> bool:
        assert station != g_station.identifier, 'neighbor station ID error: %s, %s' % (station, g_station)
        if self.__neighbors.get(station) is None:
            # create remote station
            server = g_facebook.user(identifier=station)
            assert isinstance(server, Station), 'station error: %s' % station
            if not isinstance(server, Server):
                server = Server(identifier=station, host=server.host, port=server.port)
                g_facebook.cache_user(user=server)
            # worker for remote station
            self.info('bridge for neighbor station: %s' % server)
            self.__neighbors[station] = Worker(client=Terminal(), server=server, messenger=OuterMessenger())
            return True

    def __deliver_message(self, msg: ReliableMessage, neighbor: ID) -> bool:
        if neighbor == g_station.identifier:
            worker = self.__home
        else:
            worker = self.__neighbors.get(neighbor)
            # TODO: if not connected directly, forward to the middle station
        if worker is None:
            self.error('neighbor station not defined: %s' % neighbor)
            return False
        else:
            worker.add_msg(msg=msg)
            return True

    def departure(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        receiver = msg.receiver
        if receiver == g_station.identifier:
            self.warning('msg for %s will be stopped here' % receiver)
            return None
        target = ID.parse(identifier=msg.get('target'))
        if target is None:
            # broadcast to all neighbors
            all_neighbors = self.__neighbors.keys()
            sent_neighbors = msg.get('sent_neighbors')
            if sent_neighbors is None:
                sent_neighbors = []
            else:
                msg.pop('sent_neighbors')
            sent_neighbors.append(None)  # separator for logs
            for sid in all_neighbors:
                if str(sid) in sent_neighbors:
                    self.debug('station %s in sent list, ignore this neighbor' % sid)
                elif msg_traced(msg=msg, node=sid):  # and is_broadcast_message(msg=msg):
                    self.debug('station %s in traced list, ignore this neighbor' % sid)
                elif not self.__deliver_message(msg=msg, neighbor=sid):
                    self.error('failed to broadcast message to: %s' % sid)
                else:
                    sent_neighbors.append(sid)
            self.info('message broadcast to neighbor stations: %s' % sent_neighbors)
        else:
            # redirect to single neighbor
            msg.pop('target')
            if not self.__deliver_message(msg=msg, neighbor=target):
                self.error('failed to deliver message to: %s, save roaming message' % target)
                g_database.save_message(msg=msg)
            else:
                self.info('message redirect to neighbor station: %s' % target)

    def arrival(self, msg: ReliableMessage) -> Optional[ReliableMessage]:
        sid = g_station.identifier
        if not self.__deliver_message(msg=msg, neighbor=sid):
            self.error('failed to deliver income msg: %s -> %s, %s' % (msg.sender, msg.receiver, msg.get('traces')))
            g_database.save_message(msg=msg)
        return None


def update_neighbors(station: ID, neighbors: List[Station]) -> bool:
    neighbors = [str(item.identifier) for item in neighbors]
    profile = g_facebook.document(identifier=station)
    assert profile is not None, 'failed to get profile: %s' % station
    private_key = g_facebook.private_key_for_visa_signature(identifier=station)
    assert private_key is not None, 'failed to get private key: %s' % station
    profile.set_property(key='neighbors', value=neighbors)
    profile.sign(private_key=private_key)
    return g_facebook.save_document(document=profile)


if __name__ == '__main__':

    # update for neighbor stations
    update_neighbors(station=g_station.identifier, neighbors=neighbor_stations)

    # set current user
    g_facebook.current_user = g_station

    octopus = Octopus()
    # set local station
    octopus.set_home(station=g_station.identifier)
    # add neighbors
    for node in neighbor_stations:
        assert node != g_station, 'neighbor station error: %s, %s' % (node, g_station)
        octopus.add_neighbor(station=node.identifier)
    # start all
    octopus.start()
