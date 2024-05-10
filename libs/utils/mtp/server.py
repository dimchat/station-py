# -*- coding: utf-8 -*-

import json
import socket
import traceback
from typing import Optional

from startrek import Docker, DockerStatus, DockerDelegate
from startrek import Arrival, Departure
from udp.mtp import Package, DataType
from udp import PackageArrival, PackageDocker
from udp import ServerHub as UDPServerHub

from dimples.conn import UDPServerGate

import dmtp

from ...utils import Log

from .manager import ContactManager, FieldValueEncoder


class Server(dmtp.Server, DockerDelegate):

    def __init__(self, host: str, port: int):
        super().__init__()
        self.__local_address = (host, port)
        gate = UDPServerGate(delegate=self)
        gate.hub = UDPServerHub(delegate=gate)
        self.__gate = gate
        self.__db: Optional[ContactManager] = None

    @property
    def local_address(self) -> tuple:
        return self.__local_address

    @property
    def gate(self) -> UDPServerGate:
        return self.__gate

    @property
    def hub(self) -> UDPServerHub:
        return self.gate.hub

    @property
    def database(self) -> ContactManager:
        return self.__db

    @database.setter
    def database(self, db: ContactManager):
        self.__db = db

    @property
    def identifier(self) -> str:
        return self.__db.identifier

    @identifier.setter
    def identifier(self, uid: str):
        self.__db.identifier = uid

    async def start(self):
        await self.hub.bind(address=self.local_address)
        # self.gate.start()

    def stop(self):
        # self.gate.stop()
        pass

    def info(self, msg: str):
        Log.info('%s >\t%s' % (self.__class__.__name__, msg))

    def error(self, msg: str):
        Log.error('%s >\t%s' % (self.__class__.__name__, msg))

    # Override
    def _connect(self, remote: tuple):
        try:
            self.hub.connect(remote=remote, local=self.__local_address)
        except socket.error as error:
            self.error('failed to connect to %s: %s' % (remote, error))

    # Override
    def docker_status_changed(self, previous: DockerStatus, current: DockerStatus, docker: Docker):
        remote = docker.remote_address
        local = docker.local_address
        self.info('!!! connection (%s, %s) state changed: %s -> %s' % (remote, local, previous, current))

    # Override
    def docker_received(self, ship: Arrival, docker: Docker):
        assert isinstance(ship, PackageArrival), 'arrival ship error: %s' % ship
        pack = ship.package
        if pack is not None:
            self._received(head=pack.head, body=pack.body, source=docker.remote_address)

    # Override
    def docker_sent(self, ship: Departure, docker: Docker):
        pass

    # Override
    def docker_failed(self, error: IOError, ship: Departure, docker: Docker):
        pass

    # Override
    def docker_error(self, error: IOError, ship: Departure, docker: Docker):
        pass

    # Override
    def _process_command(self, cmd: dmtp.Command, source: tuple) -> bool:
        self.info('received cmd: %s' % cmd)
        # noinspection PyBroadException
        try:
            return super()._process_command(cmd=cmd, source=source)
        except Exception as error:
            self.error('failed to process command (%s): %s' % (cmd, error))
            traceback.print_exc()
            return False

    # Override
    def _process_message(self, msg: dmtp.Message, source: tuple) -> bool:
        self.info('received msg from %s:\n\t%s' % (source, json.dumps(msg, cls=FieldValueEncoder)))
        # return super().process_message(msg=msg, source=source)
        return True

    # Override
    def send_command(self, cmd: dmtp.Command, destination: tuple) -> bool:
        self.info('sending cmd to %s:\n\t%s' % (destination, cmd))
        pack = Package.new(data_type=DataType.COMMAND, body=cmd)
        return self.send_package(pack=pack, destination=destination)

    # Override
    def send_message(self, msg: dmtp.Message, destination: tuple) -> bool:
        self.info('sending msg to %s:\n\t%s' % (destination, json.dumps(msg, cls=FieldValueEncoder)))
        pack = Package.new(data_type=DataType.MESSAGE, body=msg)
        return self.send_package(pack=pack, destination=destination)

    def send_package(self, pack: Package, destination: tuple, priority: Optional[int] = 0):
        source = self.__local_address
        worker = self.gate.fetch_docker(remote=destination, local=source, advance_party=[])
        assert isinstance(worker, PackageDocker), 'package docker error: %s' % worker
        worker.send_package(pack=pack, priority=priority)
        return True

    #
    #   Server actions
    #

    # Override
    def say_hello(self, destination: tuple) -> bool:
        if super().say_hello(destination=destination):
            return True
        cmd = dmtp.Command.hello_command(identifier=self.identifier)
        self.send_command(cmd=cmd, destination=destination)
        return True
