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

import socket
import time
from abc import ABC
from typing import Generic, TypeVar, Optional, List, Union

from startrek import Connection, ConnectionState, ActiveConnection
from startrek import Docker, DockerDelegate
from startrek import Arrival, StarGate

from ..utils import Logging, Runnable

from .mtp import TransactionID, MTPStreamDocker, MTPHelper
from .mars import MarsStreamArrival, MarsStreamDocker, MarsHelper
from .ws import WSDocker


H = TypeVar('H')


class BaseGate(StarGate, Generic[H], ABC):

    def __init__(self, delegate: DockerDelegate):
        super().__init__(delegate=delegate)
        self.__hub: H = None

    @property
    def hub(self) -> H:
        return self.__hub

    @hub.setter
    def hub(self, h: H):
        self.__hub = h

    #
    #   Docker
    #
    def get_docker(self, remote: tuple, local: Optional[tuple], advance_party: List[bytes]) -> Docker:
        docker = self._get_docker(remote=remote, local=local)
        if docker is None:
            hub = self.hub
            # from startrek import Hub
            # assert isinstance(hub, Hub)
            conn = hub.connect(remote=remote, local=local)
            if conn is not None:
                docker = self._create_docker(connection=conn, advance_party=advance_party)
                assert docker is not None, 'failed to create docker: %s, %s' % (remote, local)
                self._set_docker(remote=remote, local=local, docker=docker)
        return docker

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
    def _heartbeat(self, connection: Connection):
        # let the client to do the job
        if isinstance(connection, ActiveConnection):
            super()._heartbeat(connection=connection)

    # Override
    def _cache_advance_party(self, data: bytes, connection: Connection) -> List[bytes]:
        # TODO: cache the advance party before decide which docker to use
        if data is None or len(data) == 0:
            return []
        else:
            return [data]

    # Override
    def _clear_advance_party(self, connection: Connection):
        # TODO: remove advance party for this connection
        pass


class CommonGate(BaseGate, Logging, Runnable, Generic[H], ABC):
    """ Gate with Hub for connections """

    def __init__(self, delegate: DockerDelegate):
        super().__init__(delegate=delegate)
        self.__running = False

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
    def connection_state_changed(self, previous: ConnectionState, current: ConnectionState, connection: Connection):
        # debug info
        if current is None or current == ConnectionState.ERROR:
            self.error(msg='connection lost: %s -> %s, %s' % (previous, current, connection))
        elif current != ConnectionState.EXPIRED and current != ConnectionState.MAINTAINING:
            self.info(msg='connection state changed: %s -> %s, %s' % (previous, current, connection))
        super().connection_state_changed(previous=previous, current=current, connection=connection)

    # # Override
    # def connection_received(self, data: bytes, connection: Connection):
    #     super().connection_received(data=data, connection=connection)
    #     self.info(msg='received %d byte(s): %s' % (len(data), connection))
    #
    # # Override
    # def connection_sent(self, sent: int, data: bytes, connection: Connection):
    #     super().connection_sent(sent=sent, data=data, connection=connection)
    #     self.info(msg='sent %d byte(s): %s' % (len(data), connection))

    # Override
    def connection_failed(self, error: Union[IOError, socket.error], data: bytes, connection: Connection):
        super().connection_failed(error=error, data=data, connection=connection)
        self.error(msg='failed to send %d byte(s): %s, remote=%s' % (len(data), error, connection.remote_address))

    # Override
    def connection_error(self, error: Union[IOError, socket.error], connection: Connection):
        super().connection_error(error=error, connection=connection)
        if isinstance(error, IOError) and str(error).startswith('failed to send: '):
            self.warning(msg='ignore socket error: %s, remote=%s' % (error, connection.remote_address))

    def get_connection(self, remote: tuple, local: Optional[tuple]) -> Optional[Connection]:
        hub = self.hub
        return hub.open(remote=remote, local=local)

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
    def _create_docker(self, connection: Connection, advance_party: List[bytes]) -> Optional[Docker]:
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
            docker = MTPStreamDocker(connection=connection)
        elif MarsStreamDocker.check(data=data):
            docker = MarsStreamDocker(connection=connection)
        elif WSDocker.check(data=data):
            docker = WSDocker(connection=connection)
        else:
            raise LookupError('failed to create docker: %s' % data)
        docker.delegate = self.delegate
        return docker


class UDPServerGate(CommonGate, Generic[H]):

    # Override
    def _create_docker(self, connection: Connection, advance_party: List[bytes]) -> Optional[Docker]:
        count = len(advance_party)
        if count == 0:
            # return MTPStreamDocker(remote=remote, local=local, gate=self)
            return None
        data = advance_party[count - 1]
        # check data format before creating docker
        if MTPStreamDocker.check(data=data):
            docker = MTPStreamDocker(connection=connection)
        else:
            raise LookupError('failed to create docker: %s' % data)
        docker.delegate = self.delegate
        return docker


#
#   Client Gates
#


class TCPClientGate(CommonGate, Generic[H]):

    def __init__(self, delegate: DockerDelegate, remote: tuple, local: Optional[tuple] = None):
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
    def _create_docker(self, connection: Connection, advance_party: List[bytes]) -> Optional[Docker]:
        docker = MTPStreamDocker(connection=connection)
        docker.delegate = self.delegate
        return docker


class UDPClientGate(CommonGate, Generic[H]):

    def __init__(self, delegate: DockerDelegate, remote: tuple, local: Optional[tuple] = None):
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
    def _create_docker(self, connection: Connection, advance_party: List[bytes]) -> Optional[Docker]:
        docker = MTPStreamDocker(connection=connection)
        docker.delegate = self.delegate
        return docker
