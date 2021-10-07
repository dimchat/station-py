# -*- coding: utf-8 -*-
#
#   Star Gate: Interfaces for network connection
#
#                                Written in 2021 by Moky <albert.moky@gmail.com>
#
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

import time
from abc import ABC
from typing import Generic, TypeVar, Optional, List

from startrek.fsm import Runnable
from startrek import Connection, ConnectionState
from startrek import GateDelegate, Docker, StarGate
from startrek import Arrival
from udp import PackageDocker

from .mtp import MTPStreamDocker, MTPHelper
from .mars import MarsStreamArrival, MarsStreamDocker, MarsHelper
from .ws import WSDocker


H = TypeVar('H')


class CommonGate(StarGate, Runnable, Generic[H], ABC):
    """ Gate with Hub for connections """

    def __init__(self, delegate: GateDelegate):
        super().__init__(delegate=delegate)
        self.__running = False
        self.__hub: H = None

    @property
    def hub(self) -> H:
        return self.__hub

    @hub.setter
    def hub(self, h: H):
        self.__hub = h

    def start(self):
        self.__running = True

    def stop(self):
        self.__running = False

    @property
    def running(self) -> bool:
        return self.__running

    # Override
    def run(self):
        while self.running:
            if not self.process():
                self._idle()
        self.info('gate closing')

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.25)

    # Override
    def process(self):
        hub = self.hub
        # from tcp import Hub
        # assert isinstance(hub, Hub)
        incoming = hub.process()
        outgoing = super().process()
        return incoming or outgoing

    # Override
    def get_connection(self, remote: tuple, local: Optional[tuple]) -> Optional[Connection]:
        hub = self.hub
        # from tcp import Hub
        # assert isinstance(hub, Hub)
        return hub.connect(remote=remote, local=local)

    # Override
    def cache_advance_party(self, data: bytes, source: tuple, destination: Optional[tuple],
                            connection: Connection) -> List[bytes]:
        # TODO: cache the advance party before decide which docker to use
        if data is None:
            return []
        else:
            return [data]

    # Override
    def clear_advance_party(self, source: tuple, destination: Optional[tuple], connection: Connection):
        # TODO: remove advance party for this connection
        pass

    # Override
    def connection_state_changed(self, previous: ConnectionState, current: ConnectionState, connection: Connection):
        super().connection_state_changed(previous=previous, current=current, connection=connection)
        if current != ConnectionState.EXPIRED and current != ConnectionState.MAINTAINING:
            self.info('connection state changed: %s -> %s, %s' % (previous, current, connection))

    def send_payload(self, payload: bytes, local: Optional[tuple], remote: tuple,
                     priority: int = 0, delegate: Optional[GateDelegate] = None):
        worker = self.get_docker(remote=remote, local=local, advance_party=[])
        if worker is not None:
            ship = worker.pack(payload=payload, priority=priority, delegate=delegate)
            worker.append_departure(ship=ship)
        else:
            # raise LookupError('docker error (%s, %s): %s' % (remote, local, worker))
            self.error('docker error (%s, %s): %s' % (remote, local, worker))

    def send_response(self, payload: bytes, ship: Arrival, remote: tuple, local: Optional[tuple]):
        worker = self.get_docker(remote=remote, local=local, advance_party=[])
        if isinstance(worker, MTPStreamDocker):
            pack = MTPHelper.create_message(body=payload, sn=ship.sn)
            worker.send_package(pack=pack)
        elif isinstance(worker, MarsStreamDocker):
            assert isinstance(ship, MarsStreamArrival), 'responding ship error: %s' % ship
            mars = MarsHelper.create_respond(head=ship.package.head, payload=payload)
            ship = MarsStreamDocker.create_departure(mars=mars)
            worker.send_ship(ship=ship)
        elif isinstance(worker, WSDocker):
            ship = worker.pack(payload=payload)
            worker.send_ship(ship=ship)
        else:
            raise LookupError('docker error (%s, %s): %s' % (remote, local, worker))

    @classmethod
    def info(cls, msg: str):
        now = time.time()
        prefix = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
        print('[%s] %s' % (prefix, msg))

    @classmethod
    def error(cls, msg: str):
        print('[ERROR] ', msg)


#
#   Server Gates
#


class TCPServerGate(CommonGate, Generic[H]):

    # Override
    def create_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        count = len(advance_party)
        if count == 0:
            # return MTPStreamDocker(remote=remote, local=local, gate=self)
            return None
        data = advance_party[0]
        for i in range(1, count):
            data = data + advance_party[i]
        if len(data) == 0:
            return None
        # check data format before creating docker
        if MTPStreamDocker.check(data=data):
            return MTPStreamDocker(remote=remote, local=local, gate=self)
        if MarsStreamDocker.check(data=data):
            return MarsStreamDocker(remote=remote, local=local, gate=self)
        if WSDocker.check(data=data):
            return WSDocker(remote=remote, local=local, gate=self)


class UDPServerGate(CommonGate, Generic[H]):

    # Override
    def create_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        count = len(advance_party)
        if count == 0:
            # return PackageDocker(remote=remote, local=local, gate=self)
            return None
        data = advance_party[count - 1]
        # check data format before creating docker
        if MTPStreamDocker.check(data=data):
            return PackageDocker(remote=remote, local=local, gate=self)


#
#   Client Gates
#


class TCPClientGate(CommonGate, Generic[H]):

    # Override
    def create_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        return MTPStreamDocker(remote=remote, local=local, gate=self)


class UDPClientGate(CommonGate, Generic[H]):

    # Override
    def create_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        return PackageDocker(remote=remote, local=local, gate=self)
