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

from startrek import Connection, ConnectionState
from startrek import GateDelegate, StarGate
from startrek import Docker, Arrival

from ..utils import Logging, Runnable

from .mtp import TransactionID, MTPStreamDocker, MTPHelper
from .mars import MarsStreamArrival, MarsStreamDocker, MarsHelper
from .ws import WSDocker


H = TypeVar('H')


class CommonGate(StarGate, Logging, Runnable, Generic[H], ABC):
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
        self.__running = True
        while self.running:
            if not self.process():
                self._idle()
        self.info(msg='gate closing')

    # noinspection PyMethodMayBeStatic
    def _idle(self):
        time.sleep(0.25)

    # Override
    def get_connection(self, remote: tuple, local: Optional[tuple]) -> Optional[Connection]:
        return self.hub.connect(remote=remote, local=local)

    # Override
    def _get_docker(self, remote: tuple, local: Optional[tuple]) -> Optional[Docker]:
        return super()._get_docker(remote=remote, local=None)

    # Override
    def _set_docker(self, remote: tuple, local: Optional[tuple], docker: Docker):
        super()._set_docker(remote=remote, local=None, docker=docker)

    # Override
    def _remove_docker(self, remote: tuple, local: Optional[tuple], docker: Optional[Docker]):
        super()._remove_docker(remote=remote, local=None, docker=docker)

    # Override
    def _cache_advance_party(self, data: bytes, source: tuple, destination: Optional[tuple],
                             connection: Connection) -> List[bytes]:
        # TODO: cache the advance party before decide which docker to use
        if data is None:
            return []
        else:
            return [data]

    # Override
    def _clear_advance_party(self, source: tuple, destination: Optional[tuple], connection: Connection):
        # TODO: remove advance party for this connection
        pass

    # # Override
    # def _heartbeat(self, connection: Connection):
    #     # let the client to do the job
    #     if isinstance(connection, ActiveConnection):
    #         super()._heartbeat(connection=connection)

    # Override
    def connection_state_changed(self, previous: ConnectionState, current: ConnectionState, connection: Connection):
        # debug info
        if current is None or current == ConnectionState.ERROR:
            self.error(msg='connection lost: %s -> %s, %s' % (previous, current, connection))
        elif current != ConnectionState.EXPIRED and current != ConnectionState.MAINTAINING:
            self.info(msg='connection state changed: %s -> %s, %s' % (previous, current, connection))
        super().connection_state_changed(previous=previous, current=current, connection=connection)

    # Override
    def connection_error(self, error: ConnectionError, data: Optional[bytes],
                         source: Optional[tuple], destination: Optional[tuple], connection: Optional[Connection]):
        if isinstance(error, IOError) and str(error).startswith('failed to send: '):
            self.warning(msg='ignore socket error: %s' % error)

    # # Override
    # def connection_sent(self, data: bytes, source: Optional[tuple], destination: tuple, connection: Connection):
    #     super().connection_sent(data=data, source=source, destination=destination, connection=connection)
    #     self.info(msg='sent %d byte(s): %s -> %s' % (len(data), source, destination))

    def get_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        worker = self._get_docker(remote=remote, local=local)
        if worker is None:
            worker = self._create_docker(remote=remote, local=local, advance_party=advance_party)
            # assert worker is not None, 'failed to create docker: %s, %s' % (destination, source)
            self._set_docker(remote=worker.remote_address, local=worker.local_address, docker=worker)
        return worker

    def send_payload(self, payload: bytes, remote: tuple, local: Optional[tuple],
                     priority: int = 0, delegate: Optional[GateDelegate] = None) -> bool:
        worker = self.get_docker(remote=remote, local=local, advance_party=[])
        if worker is not None:
            ship = worker.pack(payload=payload, priority=priority, delegate=delegate)
            return worker.append_departure(ship=ship)

    def send_response(self, payload: bytes, ship: Arrival, remote: tuple, local: Optional[tuple]) -> bool:
        worker = self.get_docker(remote=remote, local=local, advance_party=[])
        if isinstance(worker, MTPStreamDocker):
            sn = TransactionID.from_data(data=ship.sn)
            pack = MTPHelper.create_message(body=payload, sn=sn)
            worker.send_package(pack=pack)
            return True
        elif isinstance(worker, MarsStreamDocker):
            assert isinstance(ship, MarsStreamArrival), 'responding ship error: %s' % ship
            mars = MarsHelper.create_respond(head=ship.package.head, payload=payload)
            ship = MarsStreamDocker.create_departure(mars=mars)
            worker.send_ship(ship=ship)
            return True
        elif isinstance(worker, WSDocker):
            ship = worker.pack(payload=payload)
            worker.send_ship(ship=ship)
            return True
        else:
            raise LookupError('docker error (%s, %s): %s' % (remote, local, worker))


#
#   Server Gates
#


class TCPServerGate(CommonGate, Generic[H]):

    # Override
    def _create_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        conn = self.get_connection(remote=remote, local=local)
        if conn is None or not conn.alive:
            self.error(msg='connection lost, could not create docker: %s -> %s' % (remote, local))
            return None
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
            return MTPStreamDocker(remote=remote, local=None, gate=self)
        if MarsStreamDocker.check(data=data):
            return MarsStreamDocker(remote=remote, local=None, gate=self)
        if WSDocker.check(data=data):
            return WSDocker(remote=remote, local=None, gate=self)


class UDPServerGate(CommonGate, Generic[H]):

    # Override
    def _create_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        conn = self.get_connection(remote=remote, local=local)
        if conn is None or not conn.alive:
            self.error(msg='connection lost, could not create docker: %s -> %s' % (remote, local))
            return None
        count = len(advance_party)
        if count == 0:
            # return MTPStreamDocker(remote=remote, local=local, gate=self)
            return None
        data = advance_party[count - 1]
        # check data format before creating docker
        if MTPStreamDocker.check(data=data):
            return MTPStreamDocker(remote=remote, local=None, gate=self)


#
#   Client Gates
#


class TCPClientGate(CommonGate, Generic[H]):

    def __init__(self, delegate: GateDelegate, remote: tuple, local: tuple = None):
        super().__init__(delegate=delegate)
        self.__remote = remote
        self.__local = local

    @property
    def remote_address(self) -> tuple:
        return self.__remote

    @property
    def local_address(self) -> Optional[tuple]:
        return self.__local

    # Override
    def _create_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        return MTPStreamDocker(remote=remote, local=None, gate=self)


class UDPClientGate(CommonGate, Generic[H]):

    def __init__(self, delegate: GateDelegate, remote: tuple, local: tuple = None):
        super().__init__(delegate=delegate)
        self.__remote = remote
        self.__local = local

    @property
    def remote_address(self) -> tuple:
        return self.__remote

    @property
    def local_address(self) -> Optional[tuple]:
        return self.__local

    # Override
    def _create_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Optional[Docker]:
        return MTPStreamDocker(remote=remote, local=None, gate=self)
