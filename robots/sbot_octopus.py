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
import traceback
from typing import Optional, Union, Dict, List

from dimsdk import ID, ReliableMessage
from dimsdk import ContentType
from dimsdk import Station

from startrek import DeparturePriority

curPath = os.path.abspath(os.path.dirname(__file__))
rootPath = os.path.split(curPath)[0]
sys.path.append(rootPath)

from libs.utils.log import Logging
from libs.utils.ipc import OctopusPipe
from libs.utils import Runner
from libs.common import msg_traced, is_broadcast_message
from libs.common import HandshakeCommand
from libs.common import CommonFacebook
from libs.client import Server, Terminal, ClientMessenger

from etc.cfg_init import neighbor_stations, g_database, g_facebook
from robots.config import dims_connect, current_station, station_id


class OctopusMessenger(ClientMessenger):
    """ Messenger for processing message from remote station """

    def __init__(self, facebook: CommonFacebook):
        super().__init__(facebook=facebook)
        self.__accepted = False

    @property
    def accepted(self) -> bool:
        return self.__accepted

    def _is_handshaking(self, msg: ReliableMessage) -> bool:
        if msg.receiver != station_id or msg.type != ContentType.COMMAND:
            # only check Command sent to this station
            return False
        i_msg = self.decrypt_message(msg=msg)
        if i_msg is not None:
            return isinstance(i_msg.content, HandshakeCommand)

    # Override
    def _broadcast_login(self, identifier: ID = None):
        self.__accepted = True
        self.info('start bridge for: %s' % self.server)
        super()._broadcast_login(identifier=identifier)

    # Override
    def process_reliable_message(self, msg: ReliableMessage) -> List[ReliableMessage]:
        # check for HandshakeCommand
        if self._is_handshaking(msg=msg):
            self.info('outer handshaking: %s' % msg.sender)
            return super().process_reliable_message(msg=msg)
        elif msg.receiver == msg.sender:
            traces = msg.get('traces')
            self.error('drop outer msg(type=%d): %s -> %s | %s' % (msg.type, msg.sender, msg.receiver, traces))
        else:
            # handshake accepted, receiving message
            self.info('incoming msg(type=%d): %s -> %s | %s' % (msg.type, msg.sender, msg.receiver, msg.get('traces')))
            g_database.save_message(msg=msg)
            g_octopus.send(msg=msg)
        return []


class Worker(Runner, Logging):
    """ Client-Server connection keeper """

    def __init__(self, client: Terminal, server: Server, messenger: OctopusMessenger):
        super().__init__()
        self.__waiting_list: List[ReliableMessage] = []  # sending messages
        self.__lock = threading.Lock()
        self.__client = dims_connect(terminal=client, server=server, user=g_facebook.current_user, messenger=messenger)
        self.__server = server
        self.__messenger = messenger

    @property
    def client(self) -> Terminal:
        return self.__client

    @property
    def server(self) -> Server:
        return self.__server

    @property
    def messenger(self) -> OctopusMessenger:
        return self.__messenger

    def add_msg(self, msg: ReliableMessage):
        with self.__lock:
            self.__waiting_list.append(msg)

    def pop_msg(self) -> Optional[ReliableMessage]:
        with self.__lock:
            if len(self.__waiting_list) > 0:
                return self.__waiting_list.pop(0)

    def msg_cnt(self) -> int:
        with self.__lock:
            return len(self.__waiting_list)

    def start(self):
        self.info('octopus starting: %s' % self.server)
        threading.Thread(target=self.run, daemon=True).start()

    # Override
    def process(self) -> bool:
        try:
            if not self.messenger.accepted:
                # handshake first
                return False
            msg = self.pop_msg()
            if msg is None:
                # nothing to do now
                return False
            elif is_broadcast_message(msg=msg):
                priority = DeparturePriority.SLOWER
            else:
                priority = DeparturePriority.NORMAL
            # send to neighbour station
            if self.messenger.send_reliable_message(msg=msg, priority=priority):
                return True
            else:
                self.error('failed to send message, store it: %s -> %s' % (msg.sender, msg.receiver))
        except Exception as error:
            self.error('octopus error: %s -> %s' % (self.server, error))
            traceback.print_exc()


class OctopusWorker(Runner, Logging):

    def __init__(self):
        super().__init__()
        self.__neighbors: Dict[ID, Worker] = {}  # ID -> Worker
        self.__pipe = OctopusPipe.secondary()

    def start(self):
        self.__pipe.start()
        # remote stations
        for sid in self.__neighbors:
            self.__neighbors[sid].start()
        self.run()

    def stop(self):
        # remote station
        for sid in self.__neighbors:
            self.__neighbors[sid].stop()
        super().stop()

    def add_neighbor(self, station: ID) -> bool:
        assert station != station_id, 'neighbor station ID error: %s, %s' % (station, station_id)
        if self.__neighbors.get(station) is None:
            # create remote station
            server = g_facebook.user(identifier=station)
            assert isinstance(server, Station), 'station error: %s' % station
            if not isinstance(server, Server):
                server = Server(identifier=station, host=server.host, port=server.port)
                g_facebook.cache_user(user=server)
            # worker for remote station
            messenger = OctopusMessenger(facebook=g_facebook)
            self.info('bridge for neighbor station: %s' % server)
            self.__neighbors[station] = Worker(client=Terminal(), server=server, messenger=messenger)
            return True

    def send(self, msg: Union[dict, ReliableMessage]):
        if isinstance(msg, ReliableMessage):
            msg = msg.dictionary
        self.__pipe.send(obj=msg)

    # Override
    def process(self) -> bool:
        msg = None
        try:
            msg = self.__pipe.receive()
            msg = ReliableMessage.parse(msg=msg)
            if msg is None:
                return False
            if msg.receiver == station_id:
                self.warning('msg for %s will be stopped here' % msg.receiver)
            else:
                self.__departure(msg=msg)
            return True
        except Exception as error:
            self.error('octopus error: %s, %s' % (msg, error))
            traceback.print_exc()

    def __departure(self, msg: ReliableMessage):
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
                    sent_neighbors.append(str(sid))
            self.info('message broadcast to neighbor stations: %s' % sent_neighbors)
        else:
            # redirect to single neighbor
            msg.pop('target')
            if self.__deliver_message(msg=msg, neighbor=target):
                self.info('message redirect to neighbor station: %s' % target)
            else:
                self.error('failed to deliver message to: %s, save roaming message' % target)

    def __deliver_message(self, msg: ReliableMessage, neighbor: ID) -> bool:
        worker = self.__neighbors.get(neighbor)
        # TODO: if not connected directly, forward to the middle station
        if worker is None:
            self.error('neighbor station not defined: %s' % neighbor)
            return False
        else:
            worker.add_msg(msg=msg)
            return True


def update_neighbors(station: ID, neighbors: List[Station]) -> bool:
    neighbors = [str(item.identifier) for item in neighbors]
    doc = g_facebook.document(identifier=station)
    assert doc is not None, 'failed to get document: %s' % station
    private_key = g_facebook.private_key_for_visa_signature(identifier=station)
    assert private_key is not None, 'failed to get private key: %s' % station
    doc.set_property(key='neighbors', value=neighbors)
    doc.sign(private_key=private_key)
    return g_facebook.save_document(document=doc)


if __name__ == '__main__':

    decrypt_keys = g_facebook.private_keys_for_decryption(identifier=station_id)
    assert len(decrypt_keys) > 0, 'failed to get decrypt keys for current station: %s' % station_id
    print('Current station with %d private key(s): %s' % (len(decrypt_keys), station_id))

    # update for neighbor stations
    update_neighbors(station=station_id, neighbors=neighbor_stations)

    # set current user
    g_facebook.current_user = current_station()

    g_octopus = OctopusWorker()
    # add neighbors
    for node in neighbor_stations:
        assert node.identifier != station_id, 'neighbor station error: %s, current station: %s' % (node, station_id)
        g_octopus.add_neighbor(station=node.identifier)
    # start all
    g_octopus.start()
