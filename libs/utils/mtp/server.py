# -*- coding: utf-8 -*-

import json
import socket
import traceback
from typing import Optional

from udp.mtp import Package, DataType

from ...network import Connection, Gate, GateStatus, GateDelegate
from ...network import Arrival, Departure, ShipDelegate
from ...network import PackageArrival, PackageDocker, PackageHub, UDPGate

import dmtp

from ...utils import Log

from .manager import ContactManager, FieldValueEncoder


class Server(dmtp.Server, GateDelegate):

    def __init__(self, host: str, port: int):
        super().__init__()
        self.__local_address = (host, port)
        gate = UDPGate(delegate=self)
        gate.hub = PackageHub(delegate=gate)
        self.__gate = gate
        self.__db: Optional[ContactManager] = None

    @property
    def local_address(self) -> tuple:
        return self.__local_address

    @property
    def gate(self) -> UDPGate:
        return self.__gate

    @property
    def hub(self) -> PackageHub:
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

    def start(self):
        self.hub.bind(address=self.local_address)
        self.gate.start()

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
    def gate_status_changed(self, previous: GateStatus, current: GateStatus,
                            remote: tuple, local: Optional[tuple], gate: Gate):
        self.info('!!! connection (%s, %s) state changed: %s -> %s' % (remote, local, previous, current))

    # Override
    def gate_received(self, ship: Arrival, source: tuple, destination: Optional[tuple], connection: Connection):
        assert isinstance(ship, PackageArrival), 'arrival ship error: %s' % ship
        pack = ship.package
        if pack is not None:
            self._received(head=pack.head, body=pack.body, source=source)

    def gate_sent(self, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
        pass

    def gate_error(self, error, ship: Departure, source: Optional[tuple], destination: tuple, connection: Connection):
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

    def send_package(self, pack: Package, destination: tuple,
                     priority: Optional[int] = 0, delegate: Optional[ShipDelegate] = None):
        source = self.__local_address
        worker = self.gate.get_docker(remote=destination, local=source, advance_party=[])
        assert isinstance(worker, PackageDocker), 'package docker error: %s' % worker
        worker.send_package(pack=pack, priority=priority, delegate=delegate)
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
